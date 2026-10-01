from __future__ import annotations

from copy import deepcopy

from eye_collector.etl.parser import parse_snapshot


def test_parser_reads_only_explicit_fields_and_preserves_raw_payload() -> None:
    payload = {
        "name": "  测试医院（东院） ",
        "address": "北京市朝阳区测试路 1 号",
        "phone": "010-12345678",
        "administrative_code": "110105",
        "registration_id": "REG-001",
        "campus_name": "东院",
        "department_text": "设有眼科门诊",
    }
    original = deepcopy(payload)

    result = parse_snapshot("snapshot-1", payload, registration_id_reliable=True)

    assert result.record is not None
    assert result.record.source_record_id == "snapshot-1"
    assert result.record.name == payload["name"]
    assert result.record.address == payload["address"]
    assert result.record.phone == payload["phone"]
    assert result.record.administrative_code == "110105"
    assert result.record.registration_id == "REG-001"
    assert result.record.registration_id_reliable is True
    assert result.record.raw_payload == original
    assert payload == original
    assert result.skip_reason is None


def test_parser_does_not_infer_administrative_code_from_address() -> None:
    result = parse_snapshot(
        "snapshot-2",
        {"name": "测试医院", "address": "北京市朝阳区测试路 2 号"},
        registration_id_reliable=False,
    )

    assert result.record is not None
    assert result.record.administrative_code is None


def test_parser_skips_records_without_a_nonblank_name() -> None:
    result = parse_snapshot("snapshot-3", {"name": "  ", "address": "某处"})

    assert result.record is None
    assert result.skip_reason == "missing_name"
