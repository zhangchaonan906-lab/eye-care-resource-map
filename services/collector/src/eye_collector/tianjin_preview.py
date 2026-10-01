from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from eye_collector.etl.evidence import extract_ophthalmology_evidence
from eye_collector.etl.normalization import normalize_record
from eye_collector.etl.parser import parse_snapshot
from eye_collector.sources.open_data_file import (
    TIANJIN_REGISTRATION_PREVIEW,
    OpenDataFileAdapter,
    OpenDataFileInspection,
    inspect_open_data_file,
)

_DISTRICTS = (
    "和平区",
    "河东区",
    "河西区",
    "南开区",
    "河北区",
    "红桥区",
    "东丽区",
    "津南区",
    "西青区",
    "北辰区",
    "武清区",
    "宝坻区",
    "滨海新区",
    "宁河区",
    "静海区",
    "蓟州区",
)
_ADDRESS_SEPARATORS = re.compile(r"[;；\n\r]+")
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日")


@dataclass(frozen=True, slots=True)
class TianjinRegistrationPreview:
    inspection: OpenDataFileInspection
    total_raw_rows: int
    valid_names: int
    empty_names: int
    empty_addresses: int
    duplicate_exact_name_groups: int
    duplicate_normalized_name_groups: int
    distinct_normalized_names: int
    candidate_groups: int
    rows_with_eye_evidence: int
    distinct_eye_candidate_names: int
    category_distribution: tuple[tuple[str, int], ...]
    ownership_distribution: tuple[tuple[str, int], ...]
    beds_valid: int
    beds_missing: int
    beds_invalid: int
    approval_date_min: str | None
    approval_date_max: str | None
    approval_date_invalid: int
    observed_districts: tuple[str, ...]
    multi_location_address_candidates: int


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _parse_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = _text(value)
    if not text:
        return None
    try:
        return dt.datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for date_format in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def _bed_count_status(value: object) -> str:
    text = _text(value)
    if not text:
        return "missing"
    try:
        number = Decimal(text)
    except InvalidOperation:
        return "invalid"
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        return "invalid"
    return "valid"


def _is_multi_location_address(address: str) -> bool:
    districts = {district for district in _DISTRICTS if district in address}
    if len(districts) > 1:
        return True
    parts = [part.strip() for part in _ADDRESS_SEPARATORS.split(address) if part.strip()]
    return len(parts) > 1 and sum("天津市" in part for part in parts) > 1


def _distribution(values: list[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


def preview_tianjin_registration_file(
    path: str | Path,
) -> TianjinRegistrationPreview:
    """Inspect, map, and run P3 transforms in memory without any database access."""
    inspection = inspect_open_data_file(path, TIANJIN_REGISTRATION_PREVIEW)
    if not inspection.schema_match:
        details = "; ".join(inspection.validation_errors) or "headers or row widths differ"
        raise ValueError(f"Tianjin registration workbook does not match its schema: {details}")

    records = OpenDataFileAdapter(path, TIANJIN_REGISTRATION_PREVIEW).preview_records()
    if len(records) != inspection.row_count:
        raise ValueError("preview record count does not match read-only file inspection")

    raw_names: list[str] = []
    normalized_names: list[str] = []
    eye_names: set[str] = set()
    categories: list[str] = []
    ownership: list[str] = []
    districts: set[str] = set()
    empty_names = 0
    empty_addresses = 0
    beds_valid = 0
    beds_missing = 0
    beds_invalid = 0
    dates: list[dt.date] = []
    invalid_dates = 0
    eye_rows = 0
    multi_location_candidates = 0

    for index, source_record in enumerate(records):
        payload = source_record.raw_payload
        name = _text(payload.get("name"))
        address = _text(payload.get("address"))
        if not name:
            empty_names += 1
        else:
            raw_names.append(name)
        if not address:
            empty_addresses += 1
        if address:
            districts.update(district for district in _DISTRICTS if district in address)
            multi_location_candidates += int(_is_multi_location_address(address))

        category = _text(payload.get("source_category")) or "(missing)"
        categories.append(category)
        ownership_type = _text(payload.get("ownership_type")) or "(missing)"
        ownership.append(ownership_type)

        bed_status = _bed_count_status(payload.get("bed_count"))
        if bed_status == "valid":
            beds_valid += 1
        elif bed_status == "missing":
            beds_missing += 1
        else:
            beds_invalid += 1

        raw_approval_date = payload.get("approval_date")
        approval_date = _parse_date(raw_approval_date)
        if approval_date is not None:
            dates.append(approval_date)
        elif _text(raw_approval_date):
            invalid_dates += 1

        parsed = parse_snapshot(f"tianjin-preview-{index}", payload)
        if parsed.record is None:
            continue
        normalized = normalize_record(parsed.record)
        normalized_names.append(normalized.normalized_name)
        evidence = extract_ophthalmology_evidence(parsed.record)
        if evidence.status == "evidence_found":
            eye_rows += 1
            eye_names.add(normalized.normalized_name)

    exact_counts = Counter(raw_names)
    normalized_counts = Counter(normalized_names)
    duplicate_exact_groups = sum(count > 1 for count in exact_counts.values())
    duplicate_normalized_groups = sum(count > 1 for count in normalized_counts.values())

    return TianjinRegistrationPreview(
        inspection=inspection,
        total_raw_rows=len(records),
        valid_names=len(normalized_names),
        empty_names=empty_names,
        empty_addresses=empty_addresses,
        duplicate_exact_name_groups=duplicate_exact_groups,
        duplicate_normalized_name_groups=duplicate_normalized_groups,
        distinct_normalized_names=len(normalized_counts),
        candidate_groups=len(normalized_counts),
        rows_with_eye_evidence=eye_rows,
        distinct_eye_candidate_names=len(eye_names),
        category_distribution=_distribution(categories),
        ownership_distribution=_distribution(ownership),
        beds_valid=beds_valid,
        beds_missing=beds_missing,
        beds_invalid=beds_invalid,
        approval_date_min=min(dates).isoformat() if dates else None,
        approval_date_max=max(dates).isoformat() if dates else None,
        approval_date_invalid=invalid_dates,
        observed_districts=tuple(sorted(districts)),
        multi_location_address_candidates=multi_location_candidates,
    )
