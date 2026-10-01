from __future__ import annotations

import logging
from dataclasses import replace
from typing import Protocol

from eye_collector.hashing import canonical_sha256
from eye_collector.logging_utils import safe_error_summary
from eye_collector.models import (
    ImportCounts,
    ImportResult,
    RawRecord,
    SourceDescriptor,
    SourceRegistration,
)
from eye_collector.policy import SourcePolicy
from eye_collector.sources.base import SourceAdapter


class CollectorRepository(Protocol):
    def start_approved_run(
        self,
        descriptor: SourceDescriptor,
        region_code: str,
        policy: SourcePolicy,
    ) -> tuple[str, SourceRegistration]: ...

    def snapshot_exists(self, source_id: str, record: RawRecord, content_hash: str) -> bool: ...

    def insert_snapshot(
        self, run_id: str, source_id: str, record: RawRecord, content_hash: str
    ) -> bool: ...

    def finish_run(
        self,
        run_id: str,
        status: str,
        counts: dict[str, int],
        error_summary: str | None = None,
    ) -> None: ...


class CollectorRunner:
    def __init__(
        self,
        repository: CollectorRepository,
        adapter: SourceAdapter,
        *,
        policy: SourcePolicy | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._adapter = adapter
        self._policy = policy or SourcePolicy()
        self._logger = logger or logging.getLogger("eye_collector.runner")

    def run(
        self,
        region_code: str,
        *,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> ImportResult:
        if len(region_code) != 6 or not region_code.isdigit():
            raise ValueError("region_code must contain six digits")
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")

        descriptor = self._adapter.descriptor
        counts = ImportCounts()
        requested_records = 0
        seen_in_run: set[tuple[str, str]] = set()

        def count_request() -> None:
            nonlocal counts
            counts = replace(counts, requested=counts.requested + 1)

        run_id, registration = self._repository.start_approved_run(
            descriptor, region_code, self._policy
        )
        try:
            self._log(
                logging.INFO,
                "run_started",
                run_id=run_id,
                source_id=registration.id,
                source_name=registration.name,
                region_code=region_code,
                source_key=descriptor.source_key,
            )
            self._adapter.set_request_context(
                run_id=run_id,
                source=registration,
                region_code=region_code,
            )
            for page in self._adapter.iter_pages(
                region_code, limit, on_request=count_request
            ):
                counts = replace(counts, received=counts.received + len(page.records))
                for record in page.records:
                    if limit is not None and requested_records >= limit:
                        break
                    requested_records += 1
                    self._policy.authorize_record(registration, record)
                    content_hash = canonical_sha256(record.raw_payload)
                    marker = (record.source_key, content_hash)
                    if dry_run:
                        if marker in seen_in_run or self._repository.snapshot_exists(
                            registration.id, record, content_hash
                        ):
                            counts = replace(counts, unchanged=counts.unchanged + 1)
                        else:
                            counts = replace(counts, inserted=counts.inserted + 1)
                            seen_in_run.add(marker)
                    elif self._repository.insert_snapshot(
                        run_id, registration.id, record, content_hash
                    ):
                        counts = replace(counts, inserted=counts.inserted + 1)
                    else:
                        counts = replace(counts, unchanged=counts.unchanged + 1)

                if limit is not None and requested_records >= limit:
                    break

            self._repository.finish_run(run_id, "succeeded", counts.as_dict())
            self._log(
                logging.INFO,
                "run_succeeded",
                run_id=run_id,
                source_id=registration.id,
                source_name=registration.name,
                region_code=region_code,
                source_key=descriptor.source_key,
            )
            return ImportResult(run_id, "succeeded", counts, dry_run)
        except KeyboardInterrupt:
            self._repository.finish_run(
                run_id, "cancelled", counts.as_dict(), "Collection interrupted by operator"
            )
            self._log(
                logging.WARNING,
                "run_cancelled",
                run_id=run_id,
                source_id=registration.id,
                source_name=registration.name,
                region_code=region_code,
                source_key=descriptor.source_key,
            )
            raise
        except Exception as error:
            summary = safe_error_summary(error)
            counts = replace(counts, failed=counts.failed + 1)
            self._repository.finish_run(run_id, "failed", counts.as_dict(), summary)
            self._log(
                logging.ERROR,
                "run_failed",
                run_id=run_id,
                source_id=registration.id,
                source_name=registration.name,
                region_code=region_code,
                source_key=descriptor.source_key,
                error=summary,
            )
            return ImportResult(run_id, "failed", counts, dry_run)

    def _log(self, level: int, event: str, **fields: object) -> None:
        self._logger.log(level, event, extra={"event": event, **fields})
