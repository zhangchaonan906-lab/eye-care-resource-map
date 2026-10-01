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


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    source_record_id: str
    original_name: str
    normalized_name: str
    original_address: str | None
    normalized_address: str | None
    original_phone: str | None
    normalized_phone: str | None
    administrative_code: str | None
    registration_id: str | None
    registration_id_reliable: bool
    campus_name: str | None
    raw_payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class OphthalmologyEvidence:
    source_record_id: str
    field_name: str
    evidence_text: str
    evidence_type: str = "explicit_field_mention"


@dataclass(frozen=True, slots=True)
class EvidenceExtraction:
    status: str
    evidence: tuple[OphthalmologyEvidence, ...]


@dataclass(frozen=True, slots=True)
class FacilityTarget:
    facility_id: str
    name: str
    campus_name: str | None
    administrative_code: str
    registration_id: str | None


@dataclass(frozen=True, slots=True)
class MatchResult:
    status: str
    facility_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    source_record_id: str
    raw_payload: Mapping[str, object]
    registration_id_reliable: bool


@dataclass(frozen=True, slots=True)
class PipelineStats:
    source_records_read: int = 0
    candidates_created: int = 0
    already_processed: int = 0
    skipped: int = 0
    evidence_created: int = 0
    matched: int = 0
    needs_review: int = 0
    duplicate_cases: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "source_records_read": self.source_records_read,
            "candidates_created": self.candidates_created,
            "already_processed": self.already_processed,
            "skipped": self.skipped,
            "evidence_created": self.evidence_created,
            "matched": self.matched,
            "needs_review": self.needs_review,
            "duplicate_cases": self.duplicate_cases,
            "errors": self.errors,
        }
