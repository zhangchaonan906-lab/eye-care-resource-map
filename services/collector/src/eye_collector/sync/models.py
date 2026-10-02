from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SyncTask:
    id: str
    source_sync_policy_id: str
    source_id: str
    region_code: str
    adapter_key: str
    trigger: str
    status: str
    stage: str
    attempt_count: int
    not_before: datetime
    run_timeout_seconds: int
    max_attempts: int
    backoff_base_seconds: int
    max_backoff_seconds: int
    pause_after_failures: int
    lease_owner: str
    import_run_id: str | None
    counts: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> SyncTask:
        return cls(
            id=str(row["id"]),
            source_sync_policy_id=str(row["source_sync_policy_id"]),
            source_id=str(row["source_id"]),
            region_code=str(row["region_code"]),
            adapter_key=str(row["adapter_key"]),
            trigger=str(row["trigger"]),
            status=str(row["status"]),
            stage=str(row["stage"]),
            attempt_count=int(row["attempt_count"]),
            not_before=row["not_before"],
            run_timeout_seconds=int(row["run_timeout_seconds"]),
            max_attempts=int(row["max_attempts"]),
            backoff_base_seconds=int(row["backoff_base_seconds"]),
            max_backoff_seconds=int(row["max_backoff_seconds"]),
            pause_after_failures=int(row["pause_after_failures"]),
            lease_owner=str(row["lease_owner"]),
            import_run_id=str(row["import_run_id"]) if row["import_run_id"] else None,
            counts=dict(row["counts"]),
        )
