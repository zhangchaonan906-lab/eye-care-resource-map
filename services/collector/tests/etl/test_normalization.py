from __future__ import annotations

from eye_collector.etl.models import ParsedRecord
from eye_collector.etl.normalization import normalize_record


def record(**overrides: object) -> ParsedRecord:
    values: dict[str, object] = {
        "source_record_id": "snapshot-1",
        "name": "  ＡＢＣ　医院（东院），　门诊  ",
        "address": "  北京市  朝阳区，　建国路　１号  ",
        "phone": "＋８６（010） 1234－5678",
        "administrative_code": None,
        "registration_id": None,
        "registration_id_reliable": False,
        "campus_name": None,
        "raw_payload": {},
    }
    values.update(overrides)
    return ParsedRecord(**values)  # type: ignore[arg-type]


def test_normalizes_unicode_whitespace_and_common_punctuation_without_losing_name() -> None:
    parsed = record()

    normalized = normalize_record(parsed)

    assert normalized.original_name == "  ＡＢＣ　医院（东院），　门诊  "
    assert normalized.normalized_name == "abc 医院(东院), 门诊"
    assert normalized.original_address == "  北京市  朝阳区，　建国路　１号  "
    assert normalized.normalized_address == "北京市 朝阳区, 建国路 1号"
    assert parsed.name == "  ＡＢＣ　医院（东院），　门诊  "


def test_normalizes_fullwidth_phone_digits_and_country_prefix() -> None:
    normalized = normalize_record(record())

    assert normalized.original_phone == "＋８６（010） 1234－5678"
    assert normalized.normalized_phone == "01012345678"


def test_does_not_infer_missing_administrative_code_from_address() -> None:
    normalized = normalize_record(record(administrative_code=None))

    assert normalized.normalized_address == "北京市 朝阳区, 建国路 1号"
    assert normalized.administrative_code is None


def test_missing_optional_values_stay_missing() -> None:
    normalized = normalize_record(record(address=None, phone=None, name="医院"))

    assert normalized.normalized_address is None
    assert normalized.normalized_phone is None
