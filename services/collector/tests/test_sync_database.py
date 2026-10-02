from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg
import pytest

from eye_collector.config import CollectorConfig
from eye_collector.sync.repository import SyncRepository
from eye_collector.sync.worker import SyncWorker

pytestmark = pytest.mark.database


def test_scheduled_fixture_task_collects_etl_and_completes_without_publication() -> None:
    admin_url = os.getenv("DATABASE_ADMIN_URL", "")
    sync_url = os.getenv("SYNC_DATABASE_URL", "")
    collector_url = os.getenv("DATABASE_URL", "")
    etl_url = os.getenv("ETL_DATABASE_URL", "")
    if not all((admin_url, sync_url, collector_url, etl_url)):
        pytest.skip("P12 database runtime URLs are required")

    with psycopg.connect(admin_url, autocommit=True) as connection:
        source_id = connection.execute(
            "SELECT id FROM app_private.source_catalog WHERE name='Fixture Directory'"
        ).fetchone()[0]
        policy_id = connection.execute(
            """INSERT INTO app_private.source_sync_policies
               (source_id,region_code,adapter_key,enabled,interval_minutes,next_due_at)
               VALUES (%s,'110000','fixture',true,60,%s) RETURNING id""",
            (source_id, datetime.now(UTC)),
        ).fetchone()[0]

    sync_repository = SyncRepository.connect(sync_url)
    try:
        assert sync_repository.enqueue_due(datetime.now(UTC)) == 1
        worker = SyncWorker(
            sync_repository,
            CollectorConfig(database_url=collector_url),
            etl_url,
            worker_id="p12-integration-worker",
        )
        assert worker.run_once() is True
    finally:
        sync_repository.close()

    with psycopg.connect(admin_url, autocommit=True) as connection:
        row = connection.execute(
            """SELECT status,stage,import_run_id,counts,last_error_code
               FROM app_private.source_sync_tasks WHERE source_sync_policy_id=%s""",
            (policy_id,),
        ).fetchone()
        assert row is not None
        assert row[0:2] == ("succeeded", "complete")
        assert row[2] is not None
        assert row[3]["collection"]["unchanged"] >= 0
        assert "etl" in row[3]
        assert row[4] is None
        assert connection.execute("SELECT count(*) FROM app_private.facilities").fetchone()[0] == 0
        connection.execute(
            "DELETE FROM app_private.source_sync_tasks WHERE source_sync_policy_id=%s",
            (policy_id,),
        )
        connection.execute("DELETE FROM app_private.source_sync_policies WHERE id=%s", (policy_id,))
