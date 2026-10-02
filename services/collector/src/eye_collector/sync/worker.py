from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime

import psycopg

from eye_collector.config import CollectorConfig
from eye_collector.db import PostgresRepository
from eye_collector.etl.pipeline import Pipeline
from eye_collector.etl.repository import ETLRepository
from eye_collector.exceptions import (
    AdapterConfigError,
    AdapterError,
    ETLFailedError,
    HttpRequestError,
    SourcePolicyError,
    TaskTimeoutError,
)
from eye_collector.http import HttpClient
from eye_collector.logging_utils import safe_error_summary
from eye_collector.runner import CollectorRunner
from eye_collector.sources.fixture import FixtureTransport
from eye_collector.sync.failures import classify_failure
from eye_collector.sync.registry import AdapterRegistry
from eye_collector.sync.repository import SyncRepository


class SyncWorker:
    """Claims and processes one durable task; all adapter traffic is allowlisted."""

    def __init__(
        self,
        sync_repository: SyncRepository,
        collector_config: CollectorConfig,
        etl_database_url: str,
        *,
        worker_id: str,
        registry: AdapterRegistry | None = None,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        logger: logging.Logger | None = None,
    ) -> None:
        self._sync = sync_repository
        self._collector_config = collector_config
        self._etl_database_url = etl_database_url
        self._worker_id = worker_id
        self._registry = registry or AdapterRegistry()
        self._clock = clock
        self._now = now
        self._logger = logger or logging.getLogger("eye_collector.sync.worker")

    def run_once(self) -> bool:
        task = self._sync.claim(self._worker_id, 600, self._now())
        if task is None:
            return False
        started = self._clock()
        deadline = started + task.run_timeout_seconds
        collector: PostgresRepository | None = None
        etl: ETLRepository | None = None
        http: HttpClient | None = None
        try:
            approved = self._sync.approved_source_descriptor(task.source_id)
            if approved is None:
                raise RuntimeError("approved automated source descriptor is unavailable")
            descriptor = self._registry.descriptor(task.adapter_key)
            self._registry.verify_catalog_descriptor(descriptor, approved)

            def checkpoint(import_run_id: str | None = None) -> None:
                if self._clock() >= deadline:
                    raise TaskTimeoutError("sync task exceeded configured runtime")
                if not self._sync.heartbeat(
                    task.id, self._worker_id, 600, self._now()
                ):
                    raise RuntimeError("sync task lease was lost")

            task_import_run_id: str | None
            if task.stage == "collect":
                checkpoint()
                collector = PostgresRepository.connect(self._collector_config.database_url)
                http = HttpClient(
                    timeout_seconds=self._collector_config.http_timeout_seconds,
                    max_response_bytes=self._collector_config.http_max_response_bytes,
                    max_attempts=self._collector_config.http_max_attempts,
                    backoff_base_seconds=self._collector_config.http_backoff_base_seconds,
                    user_agent=self._collector_config.http_user_agent,
                    transport=FixtureTransport(
                        revision=getattr(self._registry, "fixture_revision", "stable")
                    ),
                )
                adapter = self._registry.create(task.adapter_key, http)
                result = CollectorRunner(collector, adapter).run(
                    task.region_code,
                    on_page_boundary=lambda run_id: checkpoint(run_id),
                )
                if result.status != "succeeded":
                    summary = result.error_summary or "source collection failed"
                    if result.error_type == "SourcePolicyError":
                        raise SourcePolicyError(summary)
                    if result.error_type == "AdapterError":
                        raise AdapterError(summary)
                    if result.error_type == "AdapterConfigError":
                        raise AdapterConfigError(summary)
                    if result.error_type == "HttpRequestError":
                        raise HttpRequestError(summary)
                    if result.error_type == "OperationalError":
                        raise psycopg.OperationalError(summary)
                    raise RuntimeError("source collection failed")
                checkpoint(result.run_id)
                if not self._sync.record_collection(
                    task.id,
                    self._worker_id,
                    result.run_id,
                    result.counts.as_dict(),
                    self._now(),
                ):
                    raise RuntimeError("could not persist collected import run")
                task_import_run_id = result.run_id
                collection_counts = result.counts.as_dict()
            else:
                task_import_run_id = task.import_run_id
                collection_counts = task.counts.get("collection", {})
            if not task_import_run_id:
                raise RuntimeError("ETL stage has no associated import run")

            checkpoint(task_import_run_id)
            etl = ETLRepository.connect(self._etl_database_url)
            stats = Pipeline(etl).run(
                import_run_id=task_import_run_id,
                on_checkpoint=lambda: checkpoint(task_import_run_id),
            )
            if stats.errors:
                raise ETLFailedError("scoped ETL reported record processing errors")
            checkpoint(task_import_run_id)
            counts = {
                "collection": collection_counts,
                "etl": stats.as_dict(),
                "duration_ms": max(0, int((self._clock() - started) * 1000)),
            }
            if not self._sync.complete(task.id, self._worker_id, counts, self._now()):
                raise RuntimeError("sync task completion lost its lease")
            self._logger.info(
                "source_sync_succeeded",
                extra={"event": "source_sync_succeeded", "task_id": task.id,
                       "source_id": task.source_id, "region_code": task.region_code,
                       "attempt": task.attempt_count, "stage": "complete",
                       "import_run_id": task_import_run_id, "counts": counts,
                       "duration_ms": counts["duration_ms"]},
            )
            return True
        except Exception as error:
            failure = classify_failure(error)
            summary = safe_error_summary(error)
            self._sync.retry(
                task.id, self._worker_id, failure.code, summary, failure.retryable, self._now()
            )
            self._logger.error(
                "source_sync_failed",
                extra={"event": "source_sync_failed", "task_id": task.id,
                       "source_id": task.source_id, "region_code": task.region_code,
                       "attempt": task.attempt_count, "stage": task.stage,
                       "import_run_id": task.import_run_id, "error_code": failure.code,
                       "error": summary, "duration_ms": max(0, int((self._clock()-started)*1000))},
            )
            return True
        finally:
            if http is not None:
                http.close()
            if collector is not None:
                collector.close()
            if etl is not None:
                etl.close()
