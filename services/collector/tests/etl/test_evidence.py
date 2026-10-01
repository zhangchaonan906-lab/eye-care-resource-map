from __future__ import annotations

from eye_collector.etl.evidence import extract_ophthalmology_evidence
from eye_collector.etl.models import ParsedRecord


def record(payload: dict[str, object]) -> ParsedRecord:
    return ParsedRecord(
        source_record_id="snapshot-42",
        name=str(payload.get("name", "综合医院")),
        address=None,
        phone=None,
        administrative_code=None,
        registration_id=None,
        registration_id_reliable=False,
        campus_name=None,
        raw_payload=payload,
    )


def test_hospital_name_alone_does_not_create_ophthalmology_evidence() -> None:
    result = extract_ophthalmology_evidence(record({"name": "示例眼科医院"}))

    assert result.evidence == ()
    assert result.status == "unknown"


def test_explicit_department_values_are_saved_as_source_evidence() -> None:
    result = extract_ophthalmology_evidence(
        record({"name": "示例综合医院", "departments": ["心内科", "眼科门诊"]})
    )

    assert result.status == "evidence_found"
    assert len(result.evidence) == 1
    evidence = result.evidence[0]
    assert evidence.source_record_id == "snapshot-42"
    assert evidence.field_name == "departments"
    assert evidence.evidence_text == "眼科门诊"


def test_explicit_service_text_is_preserved_without_claiming_verification() -> None:
    result = extract_ophthalmology_evidence(
        record(
            {
                "name": "示例医院",
                "ophthalmology_services": "设有眼科门诊（仅文本证据）",
                "department_text": "眼科诊疗信息",
            }
        )
    )

    assert result.status == "evidence_found"
    assert {item.field_name for item in result.evidence} == {
        "ophthalmology_services",
        "department_text",
    }
    assert {item.evidence_text for item in result.evidence} == {
        "设有眼科门诊（仅文本证据）",
        "眼科诊疗信息",
    }
    assert all(item.evidence_type == "explicit_field_mention" for item in result.evidence)


def test_unrelated_fields_and_nonmatching_department_values_are_ignored() -> None:
    result = extract_ophthalmology_evidence(
        record(
            {
                "name": "综合医院",
                "description": "设有眼科",
                "departments": ["内科", "外科"],
            }
        )
    )

    assert result.evidence == ()
    assert result.status == "unknown"


def test_hospital_description_requires_explicit_ophthalmology_text() -> None:
    result = extract_ophthalmology_evidence(
        record(
            {
                "hospital_description": "医院设有眼科门诊，配有相关检查设备。",
                "name": "综合医院",
            }
        )
    )

    assert result.status == "evidence_found"
    assert [(item.field_name, item.evidence_text) for item in result.evidence] == [
        ("hospital_description", "医院设有眼科门诊，配有相关检查设备。")
    ]


def test_hospital_description_without_explicit_eye_clinic_text_is_unknown() -> None:
    result = extract_ophthalmology_evidence(
        record(
            {
                "hospital_description": "医院配有眼底照相设备。",
                "name": "综合医院",
            }
        )
    )

    assert result.evidence == ()
    assert result.status == "unknown"
