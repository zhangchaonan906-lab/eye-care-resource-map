from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    id: str
    name: str
    url: str
    use_basis: str
    permitted_fields: frozenset[str]
    access_policy: str | None
    status: str


@dataclass(frozen=True, slots=True)
class RawRecord:
    source_key: str
    source_url: str
    raw_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SourcePage:
    records: tuple[RawRecord, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    source_key: str
    source_name: str
    catalog_url: str
    requests_per_second: float = 1.0
    min_delay_ms: int = 0
    max_concurrency: int = 1
    access_method: str = "http"


@dataclass(frozen=True, slots=True)
class ImportCounts:
    requested: int = 0
    received: int = 0
    inserted: int = 0
    unchanged: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "requested": self.requested,
            "received": self.received,
            "inserted": self.inserted,
            "unchanged": self.unchanged,
            "failed": self.failed,
        }


@dataclass(frozen=True, slots=True)
class ImportResult:
    run_id: str
    status: str
    counts: ImportCounts = field(default_factory=ImportCounts)
    dry_run: bool = False
