from __future__ import annotations

import re
from collections.abc import Mapping

from eye_collector.etl.models import ParsedRecord, ParseResult

_ADMINISTRATIVE_CODE = re.compile(r"^[0-9]{6}$")


def _optional_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value.strip() else None


def parse_snapshot(
    source_record_id: str,
    raw_payload: Mapping[str, object],
    *,
    registration_id_reliable: bool = False,
) -> ParseResult:
    """Map source fields without changing the original payload or inferring values."""
    name = raw_payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return ParseResult(record=None, skip_reason="missing_name")

    administrative_code = _optional_text(raw_payload, "administrative_code")
    if administrative_code is None:
        administrative_code = _optional_text(raw_payload, "adcode")
    if administrative_code is not None and not _ADMINISTRATIVE_CODE.fullmatch(
        administrative_code.strip()
    ):
        administrative_code = None

    return ParseResult(
        record=ParsedRecord(
            source_record_id=source_record_id,
            name=name,
            address=_optional_text(raw_payload, "address"),
            phone=_optional_text(raw_payload, "phone"),
            administrative_code=(
                administrative_code.strip() if administrative_code is not None else None
            ),
            registration_id=_optional_text(raw_payload, "registration_id"),
            registration_id_reliable=registration_id_reliable,
            campus_name=_optional_text(raw_payload, "campus_name"),
            raw_payload=raw_payload,
        )
    )
