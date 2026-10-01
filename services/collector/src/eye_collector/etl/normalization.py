from __future__ import annotations

import re
import unicodedata

from eye_collector.etl.models import NormalizedRecord, ParsedRecord

_PUNCTUATION = str.maketrans(
    {
        "，": ",",
        "、": ",",
        "。": ".",
        "；": ";",
        "：": ":",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "《": "<",
        "》": ">",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "—": "-",
        "–": "-",
        "－": "-",
        "／": "/",
        "＆": "&",
    }
)
_PHONE_FORMAT = re.compile(r"^[+0-9().\-/\s]+$")


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).translate(_PUNCTUATION)
    collapsed = " ".join(normalized.split()).strip()
    return collapsed.casefold() or None


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized or not _PHONE_FORMAT.fullmatch(normalized):
        return None
    compact = re.sub(r"[().\-/\s]", "", normalized)
    if compact.startswith("+86"):
        compact = compact[3:]
    elif compact.startswith("0086"):
        compact = compact[4:]
    digits = re.sub(r"\D", "", compact)
    return digits or None


def normalize_record(record: ParsedRecord) -> NormalizedRecord:
    return NormalizedRecord(
        source_record_id=record.source_record_id,
        original_name=record.name,
        normalized_name=_normalize_text(record.name) or "",
        original_address=record.address,
        normalized_address=_normalize_text(record.address),
        original_phone=record.phone,
        normalized_phone=_normalize_phone(record.phone),
        administrative_code=record.administrative_code,
        registration_id=record.registration_id,
        registration_id_reliable=record.registration_id_reliable,
        campus_name=record.campus_name,
        raw_payload=record.raw_payload,
    )
