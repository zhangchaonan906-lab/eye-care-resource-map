from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from eye_collector.sync.models import SyncTask


class SyncRepository:
    """Sync state access through the dedicated SYNC_DATABASE_URL role."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    @classmethod
    def connect(cls, database_url: str) -> SyncRepository:
        return cls(psycopg.connect(database_url, row_factory=dict_row, autocommit=True))

    def close(self) -> None:
        self._connection.close()

    def enqueue_due(self, now: datetime) -> int:
        row = self._connection.execute(
            "SELECT app_private.enqueue_due_source_sync_tasks(%s) AS queued", (now,)
        ).fetchone()
        return int(row["queued"]) if row else 0

    def claim(self, worker_id: str, lease_seconds: int, now: datetime) -> SyncTask | None:
        row = self._connection.execute(
            "SELECT * FROM app_private.claim_source_sync_task(%s,%s,%s)",
            (worker_id, lease_seconds, now),
        ).fetchone()
        return SyncTask.from_row(row) if row else None

    def approved_source_descriptor(self, source_id: str) -> dict[str, Any] | None:
        return self._connection.execute(
            "SELECT * FROM app_private.approved_sync_source_descriptor(%s)", (source_id,)
        ).fetchone()

    def heartbeat(
        self, task_id: str, worker_id: str, lease_seconds: int, now: datetime
    ) -> bool:
        row = self._connection.execute(
            "SELECT app_private.heartbeat_source_sync_task(%s,%s,%s,%s) AS extended",
            (task_id, worker_id, lease_seconds, now),
        ).fetchone()
        return bool(row["extended"]) if row else False

    def record_collection(
        self,
        task_id: str,
        worker_id: str,
        import_run_id: str,
        counts: dict[str, int],
        now: datetime,
    ) -> bool:
        row = self._connection.execute(
            "SELECT app_private.record_source_sync_collection(%s,%s,%s,%s,%s) AS recorded",
            (task_id, worker_id, import_run_id, Jsonb(counts), now),
        ).fetchone()
        return bool(row["recorded"]) if row else False

    def retry(
        self,
        task_id: str,
        worker_id: str,
        error_code: str,
        safe_summary: str,
        retryable: bool,
        now: datetime,
    ) -> str:
        row = self._connection.execute(
            "SELECT app_private.retry_source_sync_task(%s,%s,%s,%s,%s,%s) AS status",
            (task_id, worker_id, error_code, safe_summary[:500], retryable, now),
        ).fetchone()
        if row is None:
            raise RuntimeError("sync task retry transition returned no status")
        return str(row["status"])

    def complete(
        self, task_id: str, worker_id: str, counts: dict[str, Any], now: datetime
    ) -> bool:
        row = self._connection.execute(
            "SELECT app_private.complete_source_sync_task(%s,%s,%s,%s) AS completed",
            (task_id, worker_id, Jsonb(counts), now),
        ).fetchone()
        return bool(row["completed"]) if row else False
