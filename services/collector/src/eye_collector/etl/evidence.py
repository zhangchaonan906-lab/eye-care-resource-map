from __future__ import annotations

import re
from collections.abc import Mapping

from eye_collector.etl.models import (
    EvidenceExtraction,
    OphthalmologyEvidence,
    ParsedRecord,
)

_EYE_MENTION = re.compile(r"眼科|ophthalmolog", re.IGNORECASE)
_EVIDENCE_FIELDS = (
    "ophthalmology_services",
    "departments",
    "department_text",
    "specialties",
    "hospital_description",
)


def _explicit_values(field_name: str, value: object) -> tuple[str, ...]:
    if field_name == "ophthalmology_services" and value is True:
        return ("true",)
    if isinstance(value, str):
        return (value,) if _EYE_MENTION.search(value) else ()
    if isinstance(value, (tuple, list)):
        return tuple(
            item for item in value if isinstance(item, str) and _EYE_MENTION.search(item)
        )
    return ()


def extract_ophthalmology_evidence(record: ParsedRecord) -> EvidenceExtraction:
    payload: Mapping[str, object] = record.raw_payload
    evidence = tuple(
        OphthalmologyEvidence(
            source_record_id=record.source_record_id,
            field_name=field_name,
            evidence_text=text,
        )
        for field_name in _EVIDENCE_FIELDS
        for text in _explicit_values(field_name, payload.get(field_name))
    )
    return EvidenceExtraction(
        status="evidence_found" if evidence else "unknown",
        evidence=evidence,
    )
