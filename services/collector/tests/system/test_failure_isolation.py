from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from eye_collector.config import CollectorConfig
from eye_collector.exceptions import HttpRequestError
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage
from eye_collector.sources.base import SourceAdapter
from eye_collector.sync.registry import AdapterRegistry
from eye_collector.sync.repository import SyncRepository
from eye_collector.sync.worker import SyncWorker


class _RetrySource(SourceAdapter):
    def __init__(self, descriptor: SourceDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> SourceDescriptor:
        return self._descriptor

    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        raise HttpRequestError("HTTP 503 synthetic terminal retry source")


class _HealthySource(SourceAdapter):
    def __init__(self, descriptor: SourceDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> SourceDescriptor:
        return self._descriptor

    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        assert cursor is None
        return SourcePage(
            (
                RawRecord(
                    "healthy-record-1",
                    f"https://fixture.invalid/{self._descriptor.source_key}/1",
                    {
                        "name": "P13 Isolation Fixture Hospital",
                        "address": "北京市朝阳区合成测试路1号",
                        "region": region_code,
                        "administrative_code": "110105",
                        "departments": ["眼科"],
                    },
                ),
            ),
            None,
        )


class _InjectedRegistry:
    def __init__(self, descriptors: dict[str, SourceDescriptor]) -> None:
        self._descriptors = descriptors

    def descriptor(self, adapter_key: str) -> SourceDescriptor:
        return self._descriptors[adapter_key]

    def create(self, adapter_key: str, _http: Any) -> SourceAdapter:
        descriptor = self.descriptor(adapter_key)
        if adapter_key == "p13_retry_fixture":
            return _RetrySource(descriptor)
        if adapter_key == "p13_healthy_fixture":
            return _HealthySource(descriptor)
        raise AssertionError("system test registry only allows its two declared fixtures")

    @staticmethod
    def verify_catalog_descriptor(descriptor: SourceDescriptor, catalog: dict[str, Any]) -> None:
        AdapterRegistry.verify_catalog_descriptor(descriptor, catalog)


@pytest.mark.database
def test_sync_worker_isolates_retrying_source_from_healthy_source() -> None:
    admin_url = os.environ["DATABASE_ADMIN_URL"]
    sync_url = os.environ["SYNC_DATABASE_URL"]
    descriptors = {
        "p13_retry_fixture": SourceDescriptor(
            "p13-retry", "P13 Retry Isolation Fixture", "https://fixture.invalid/retry-source"
        ),
        "p13_healthy_fixture": SourceDescriptor(
            "p13-healthy", "P13 Healthy Isolation Fixture", "https://fixture.invalid/healthy-source"
        ),
    }
    source_ids: dict[str, str] = {}
    with psycopg.connect(admin_url) as connection:
        for offset, (adapter_key, descriptor) in enumerate(descriptors.items()):
            source_id = str(uuid4())
            source_ids[adapter_key] = source_id
            connection.execute(
                """INSERT INTO app_private.source_catalog
                   (id,name,url,use_basis,permitted_fields,access_policy,status,reviewed_at)
                   VALUES (%s,%s,%s,'P13 isolated synthetic adapter',
                     ARRAY['name','address','administrative_code','region','departments'],
                     'automated_access_allowed','approved',now())""",
                (source_id, descriptor.source_name, descriptor.catalog_url),
            )
            connection.execute(
                """INSERT INTO app_private.source_sync_policies
                   (source_id,region_code,adapter_key,enabled,interval_minutes,max_attempts,
                    backoff_base_seconds,max_backoff_seconds,next_due_at)
                   VALUES (%s,'110000',%s,true,60,2,1,1,
                     now()-(%s * interval '1 minute'))""",
                (source_id, adapter_key, 10 - offset),
            )

    scheduler = subprocess.run(
        [sys.executable, "-m", "eye_collector.cli", "scheduler", "--once"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"queued":2' in scheduler.stdout

    sync = SyncRepository.connect(sync_url)
    test_now = datetime.now(UTC) + timedelta(minutes=1)
    worker = SyncWorker(
        sync,
        CollectorConfig.from_env(),
        os.environ["ETL_DATABASE_URL"],
            worker_id="p13-isolation-worker",
            registry=_InjectedRegistry(descriptors),  # type: ignore[arg-type]
            now=lambda: test_now,
    )
    try:
        with psycopg.connect(admin_url) as connection:
            failed_id = connection.execute(
                "SELECT id FROM app_private.source_sync_tasks WHERE source_id=%s",
                (source_ids["p13_retry_fixture"],),
            ).fetchone()[0]
            healthy_id = connection.execute(
                "SELECT id FROM app_private.source_sync_tasks WHERE source_id=%s",
                (source_ids["p13_healthy_fixture"],),
            ).fetchone()[0]

        def task_statuses() -> tuple[str, str]:
            with psycopg.connect(admin_url) as connection:
                statuses = connection.execute(
                    """SELECT id,status FROM app_private.source_sync_tasks
                       WHERE id=ANY(%s::uuid[])""",
                    ([failed_id, healthy_id],),
                ).fetchall()
            by_id = {str(row[0]): str(row[1]) for row in statuses}
            return by_id[str(failed_id)], by_id[str(healthy_id)]

        for _ in range(4):
            failed_status, healthy_status = task_statuses()
            if failed_status == "retry_wait" and healthy_status == "succeeded":
                break
            result = worker.run_once()
            assert result is True, _task_diagnostic(admin_url, (failed_id, healthy_id))
        assert task_statuses() == ("retry_wait", "succeeded")
        with psycopg.connect(admin_url) as connection:
            assert (
                connection.execute(
                    "SELECT count(*) FROM app_private.source_records WHERE source_id=%s",
                    (source_ids["p13_healthy_fixture"],),
                ).fetchone()[0]
                == 1
            )
            assert (
                connection.execute(
                    """SELECT count(*) FROM app_private.candidate_records c
                       JOIN app_private.source_records sr ON sr.id=c.source_record_id
                       WHERE sr.source_id=%s""",
                    (source_ids["p13_healthy_fixture"],),
                ).fetchone()[0]
                == 1
            )
            connection.execute(
                """UPDATE app_private.source_sync_tasks
                   SET not_before=%s WHERE id=%s""",
                (test_now - timedelta(seconds=1), failed_id),
            )

        for _ in range(4):
            if task_statuses()[0] == "dead_letter":
                break
            result = worker.run_once()
            assert result is True, _task_diagnostic(admin_url, (failed_id, healthy_id))
        assert task_statuses()[0] == "dead_letter"
        with psycopg.connect(admin_url) as connection:
            assert connection.execute(
                "SELECT status,attempt_count FROM app_private.source_sync_tasks WHERE id=%s",
                (failed_id,),
            ).fetchone() == ("dead_letter", 2)
            assert (
                connection.execute(
                    """SELECT count(*) FROM app_private.source_sync_alerts
                       WHERE task_id=%s AND code='MAX_ATTEMPTS'""",
                    (failed_id,),
                ).fetchone()[0]
                == 1
            )
            assert (
                connection.execute(
                    "SELECT last_error_code FROM app_private.source_sync_tasks WHERE id=%s",
                    (failed_id,),
                ).fetchone()[0]
                == "HTTP_5XX"
            )
            assert (
                connection.execute(
                    """SELECT count(*) FROM app_private.source_catalog
                       WHERE id = ANY(%s::uuid[]) AND status='approved'""",
                    (list(source_ids.values()),),
                ).fetchone()[0]
                == 2
            )
    finally:
        sync.close()


def _task_diagnostic(admin_url: str, task_ids: tuple[str, str]) -> str:
    with psycopg.connect(admin_url) as connection:
        rows = connection.execute(
            """SELECT id,adapter_key,status,attempt_count,not_before,last_error_code
               FROM app_private.source_sync_tasks WHERE id=ANY(%s::uuid[])
               ORDER BY adapter_key""",
            (list(task_ids),),
        ).fetchall()
    return f"worker found no eligible task; target task states: {rows!r}"
