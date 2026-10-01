from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedRecord:
    source_record_id: str
    name: str
    address: str | None
    phone: str | None
    administrative_code: str | None
    registration_id: str | None
    registration_id_reliable: bool
    campus_name: str | None
    raw_payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ParseResult:
    record: ParsedRecord | None
    skip_reason: str | None = None
