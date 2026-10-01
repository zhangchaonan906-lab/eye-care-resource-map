from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    id: str
    name: str
    url: str
    use_basis: str
    permitted_fields: frozenset[str]
    access_policy: str | None
    status: str
    dataset_page: str | None = None
    source_updated_at: date | None = None
    pilot_group_record_limit: int | None = None
    pilot_group_record_count: int = 0


@dataclass(frozen=True, slots=True)
class FileImportProvenance:
    original_filename: str
    file_sha256: str
    file_size_bytes: int
    obtained_at: datetime
    operator: str
    acquisition_method: Literal["official_portal_manual_download"]
    member_name: str | None = None
    member_sha256: str | None = None
    member_size_bytes: int | None = None

    def __post_init__(self) -> None:
        if (
            not self.original_filename
            or "/" in self.original_filename
        ):
            raise ValueError("original_filename must contain a basename only")
        if "\\" in self.original_filename:
            raise ValueError("original_filename must not contain a path")
        if len(self.file_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.file_sha256
        ):
            raise ValueError("file_sha256 must be a lowercase SHA-256 hex digest")
        if self.file_size_bytes < 1:
            raise ValueError("file_size_bytes must be positive")
        if self.obtained_at.tzinfo is None or self.obtained_at.utcoffset() is None:
            raise ValueError("obtained_at must include a timezone offset")
        if not self.operator.strip():
            raise ValueError("operator must not be empty")
        member_values = (self.member_name, self.member_sha256, self.member_size_bytes)
        if any(value is not None for value in member_values):
            if any(value is None for value in member_values):
                raise ValueError("archive member provenance must be complete")
            assert self.member_name is not None
            assert self.member_sha256 is not None
            assert self.member_size_bytes is not None
            member_path = PurePosixPath(self.member_name)
            if (
                not self.member_name
                or "\\" in self.member_name
                or ":" in self.member_name.split("/", 1)[0]
                or member_path.is_absolute()
                or any(part in {".", ".."} for part in member_path.parts)
                or member_path.suffix.lower() != ".xlsx"
            ):
                raise ValueError("archive member name must be an XLSX basename")
            if len(self.member_sha256) != 64 or any(
                char not in "0123456789abcdef" for char in self.member_sha256
            ):
                raise ValueError("member_sha256 must be a lowercase SHA-256 hex digest")
            if not 1 <= self.member_size_bytes <= 10 * 1024 * 1024:
                raise ValueError("member_size_bytes must be between 1 and 10 MiB")


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
