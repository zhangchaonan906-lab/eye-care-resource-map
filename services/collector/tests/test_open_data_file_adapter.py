from __future__ import annotations

import csv
from pathlib import Path

import pytest
import xlwt
from openpyxl import Workbook

from eye_collector.etl.evidence import extract_ophthalmology_evidence
from eye_collector.etl.parser import parse_snapshot
from eye_collector.sources.open_data_file import (
    BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS,
    BEIJING_HOSPITALS,
    SHENZHEN_BAOAN_HOSPITALS,
    OpenDataFileAdapter,
)


def write_csv(path: Path, headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def test_csv_adapter_maps_by_named_headers_and_preserves_source_values(tmp_path: Path) -> None:
    source_file = tmp_path / "hospitals.csv"
    write_csv(
        source_file,
        ("机构名称",),
        [("北京测试医院",), ("北京眼科医院",)],
    )
    adapter = OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)

    records = list(adapter.iter_records("110000", limit=1))

    assert len(records) == 1
    assert records[0].source_key == "北京测试医院"
    assert records[0].raw_payload == {
        "name": "北京测试医院",
        "source_fields": {"机构名称": "北京测试医院"},
    }
    assert records[0].source_url == BEIJING_HOSPITALS.dataset_url
    assert adapter.descriptor.access_method == "file"


def test_adapter_fails_closed_when_any_expected_header_changes(tmp_path: Path) -> None:
    source_file = tmp_path / "designated.csv"
    write_csv(
        source_file,
        ("医院名称", "医院地址", "医院等级", "医院类别", "所属区", "定点医疗机构代码"),
        [("测试医院", "北京市东城区测试路", "三级", "综合", "东城区", "12345")],
    )
    adapter = OpenDataFileAdapter(source_file, BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS)

    with pytest.raises(ValueError, match="header schema"):
        list(adapter.iter_records("110000", limit=1))


def test_adapter_rejects_unexpected_header_and_duplicate_header(tmp_path: Path) -> None:
    for headers in (("机构名称", "电话"), ("机构名称", "机构名称")):
        source_file = tmp_path / "hospitals.csv"
        write_csv(source_file, headers, [("测试医院", "123")])
        adapter = OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)
        with pytest.raises(ValueError, match="header schema"):
            list(adapter.iter_records("110000", limit=1))


def test_adapter_rejects_inconsistent_csv_row_width(tmp_path: Path) -> None:
    source_file = tmp_path / "designated.csv"
    source_file.write_text(
        "医院地址,医院等级,医院类别,所属区,定点医疗机构编码,医院名称\n"
        "地址,三级甲等,综合,东城区,01020304\n",
        encoding="utf-8-sig",
    )
    adapter = OpenDataFileAdapter(source_file, BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS)

    with pytest.raises(ValueError, match="row width"):
        list(adapter.iter_records("110000", limit=1))


def test_adapter_rejects_unsupported_file_type(tmp_path: Path) -> None:
    source_file = tmp_path / "hospitals.json"
    source_file.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="supported formats"):
        OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)


def test_adapter_caps_one_run_and_rejects_oversized_file(tmp_path: Path) -> None:
    source_file = tmp_path / "hospitals.csv"
    write_csv(source_file, ("机构名称",), [("测试医院",)])
    adapter = OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)
    with pytest.raises(ValueError, match="explicit record limit"):
        list(adapter.iter_records("110000"))
    with pytest.raises(ValueError, match="150"):
        list(adapter.iter_records("110000", limit=151))

    source_file.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="file size"):
        OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)


def test_xlsx_adapter_uses_exact_header_names_regardless_of_column_order(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "designated.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(reversed(BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.expected_headers)))
    row = {
        "医院名称": "北京市测试医院",
        "医院地址": "北京市测试区测试路1号",
        "医院等级": "三级甲等",
        "医院类别": "综合",
        "所属区": "测试区",
        "定点医疗机构编码": "01020304",
    }
    sheet.append(
        [
            row[header]
            for header in reversed(BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.expected_headers)
        ]
    )
    workbook.save(source_file)

    adapter = OpenDataFileAdapter(source_file, BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS)
    record = next(adapter.iter_records("110000", limit=1))

    assert record.source_key == "01020304"
    assert record.raw_payload["name"] == "北京市测试医院"
    assert record.raw_payload["address"] == "北京市测试区测试路1号"
    assert record.raw_payload["registration_id"] == "01020304"
    assert record.raw_payload["source_fields"]["医院等级"] == "三级甲等"


def test_xls_adapter_reads_text_identifiers_without_numeric_coercion(tmp_path: Path) -> None:
    source_file = tmp_path / "designated.xls"
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("data")
    headers = BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.expected_headers
    row = {
        "医院名称": "北京市测试医院",
        "医院地址": "北京市测试区测试路1号",
        "医院等级": "三级甲等",
        "医院类别": "综合",
        "所属区": "测试区",
        "定点医疗机构编码": "01020304",
    }
    for column, header in enumerate(headers):
        sheet.write(0, column, header)
        sheet.write(1, column, row[header])
    workbook.save(str(source_file))

    adapter = OpenDataFileAdapter(source_file, BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS)
    record = next(adapter.iter_records("110000", limit=1))

    assert record.source_key == "01020304"
    assert record.raw_payload["registration_id"] == "01020304"


def test_shenzhen_strengths_field_can_supply_explicit_eye_evidence_without_contact_data(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "baoan.csv"
    row = {header: "" for header in SHENZHEN_BAOAN_HOSPITALS.expected_headers}
    row.update(
        {
            "ID": "row-1",
            "NAME": "宝安测试医院",
            "LOCAL": "宝安区",
            "ADDRESS": "深圳市宝安区测试路1号",
            "ADVANTAGE": "设有眼科专科门诊",
            "PHONE": "075500000000",
            "EMAIL": "private@example.test",
        }
    )
    write_csv(
        source_file,
        SHENZHEN_BAOAN_HOSPITALS.expected_headers,
        [tuple(row[header] for header in SHENZHEN_BAOAN_HOSPITALS.expected_headers)],
    )
    adapter = OpenDataFileAdapter(source_file, SHENZHEN_BAOAN_HOSPITALS)
    source_record = next(adapter.iter_records("440306", limit=1))
    parsed = parse_snapshot("source-record-1", source_record.raw_payload)

    assert parsed.record is not None
    extraction = extract_ophthalmology_evidence(parsed.record)
    assert extraction.status == "evidence_found"
    assert extraction.evidence[0].field_name == "specialties"
    assert extraction.evidence[0].evidence_text == "设有眼科专科门诊"
    assert "specialties" in source_record.raw_payload
    assert "phone" not in source_record.raw_payload
    assert "email" not in source_record.raw_payload
