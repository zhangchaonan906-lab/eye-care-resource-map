from __future__ import annotations

from eye_collector.etl.evidence import extract_ophthalmology_evidence
from eye_collector.etl.parser import parse_snapshot


def synthetic_truth_records() -> list[tuple[dict[str, object], bool]]:
    records: list[tuple[dict[str, object], bool]] = []
    for index in range(150):
        if index < 40:
            payload: dict[str, object] = {
                "name": f"合成眼科医疗机构{index:03d}",
                "address": f"北京市合成路{index}号",
                "administrative_code": "110000",
                "specialties": ["眼科门诊"],
            }
            expected_evidence = True
        elif index < 50:
            payload = {
                "name": "同名院区测试医院（东院）" if index < 45 else "同名院区测试医院（西院）",
                "address": f"北京市院区路{index}号",
                "administrative_code": "110000",
                "campus_name": "东院" if index < 45 else "西院",
                "registration_id": "SYNTHETIC-CAMPUS-001",
                "specialties": ["眼科"],
            }
            expected_evidence = True
        elif index < 75:
            payload = {"name": f"眼科名称但无科目证据医院{index:03d}", "address": "合成地址"}
            expected_evidence = False
        elif index < 100:
            payload = {
                "name": f"综合医院{index:03d}",
                "address": "合成地址",
                "departments": ["内科"],
            }
            expected_evidence = False
        elif index < 120:
            payload = {
                "name": f"缺地址医院{index:03d}",
                "administrative_code": "not-a-region",
                "department_text": "未提供诊疗科目",
            }
            expected_evidence = False
        elif index < 140:
            payload = {
                "name": f"变更快照医院{index - 120:03d}",
                "address": "合成变更地址",
                "registration_id": f"SYNTHETIC-REG-{index - 120:03d}",
            }
            expected_evidence = False
        elif index < 145:
            payload = {"name": "  ", "address": "无名称测试记录"}
            expected_evidence = False
        else:
            payload = {"name": "—", "address": "占位名称测试记录"}
            expected_evidence = False
        records.append((payload, expected_evidence))
    return records


def test_p13_deterministic_synthetic_truth_set_has_no_false_eye_evidence() -> None:
    truth = synthetic_truth_records()
    parsed_count = 0
    skipped_count = 0
    predicted_eye_count = 0
    true_positive_count = 0
    false_eye_evidence_count = 0

    for index, (payload, expected_evidence) in enumerate(truth):
        parsed = parse_snapshot(f"p13-synthetic-{index:03d}", payload)
        if parsed.record is None:
            skipped_count += 1
            assert not expected_evidence
            continue
        parsed_count += 1
        evidence = extract_ophthalmology_evidence(parsed.record)
        predicted_eye = evidence.status == "evidence_found"
        if predicted_eye:
            predicted_eye_count += 1
        if predicted_eye and expected_evidence:
            true_positive_count += 1
        if predicted_eye and not expected_evidence:
            false_eye_evidence_count += 1
        assert predicted_eye is expected_evidence

    assert len(truth) == 150
    assert parsed_count == 140
    assert skipped_count == 10
    assert predicted_eye_count == 50
    assert true_positive_count / predicted_eye_count == 1.0
    assert false_eye_evidence_count == 0
