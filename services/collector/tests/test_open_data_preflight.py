from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import xlwt
from openpyxl import Workbook

from eye_collector.sources.open_data_file import (
    BEIJING_HOSPITALS,
    OpenDataFileInspection,
    inspect_open_data_file,
)


def test_preflight_hashes_original_bytes_and_counts_all_csv_rows(tmp_path: Path) -> None:
    source_file = tmp_path / "official.csv"
    original_bytes = "机构名称\r\n医院甲\r\n医院乙\r\n".encode("utf-8-sig")
    source_file.write_bytes(original_bytes)

    inspection = inspect_open_data_file(source_file, BEIJING_HOSPITALS)

    assert inspection == OpenDataFileInspection(
        original_filename="official.csv",
        file_sha256=hashlib.sha256(original_bytes).hexdigest(),
        file_size_bytes=len(original_bytes),
        detected_format="csv",
        headers=("机构名称",),
        row_count=2,
        expected_schema=("机构名称",),
        schema_match=True,
    )
    assert source_file.read_bytes() == original_bytes


def test_preflight_reports_schema_mismatch_without_changing_file(tmp_path: Path) -> None:
    source_file = tmp_path / "changed.csv"
    source_file.write_text("机构名称,意外字段\n医院甲,值\n", encoding="utf-8-sig")
    before = source_file.read_bytes()

    inspection = inspect_open_data_file(source_file, BEIJING_HOSPITALS)

    assert inspection.schema_match is False
    assert inspection.headers == ("机构名称", "意外字段")
    assert inspection.row_count == 1
    assert source_file.read_bytes() == before


@pytest.mark.parametrize("extension", [".xls", ".xlsx"])
def test_preflight_detects_excel_format_and_counts_rows(tmp_path: Path, extension: str) -> None:
    source_file = tmp_path / f"official{extension}"
    if extension == ".xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(list(BEIJING_HOSPITALS.expected_headers))
        sheet.append(["医院甲"])
        sheet.append(["医院乙"])
        workbook.save(source_file)
    else:
        workbook_xls = xlwt.Workbook()
        sheet_xls = workbook_xls.add_sheet("Sheet1")
        sheet_xls.write(0, 0, "机构名称")
        sheet_xls.write(1, 0, "医院甲")
        sheet_xls.write(2, 0, "医院乙")
        workbook_xls.save(str(source_file))

    inspection = inspect_open_data_file(source_file, BEIJING_HOSPITALS)

    assert inspection.detected_format == extension.removeprefix(".")
    assert inspection.row_count == 2
    assert inspection.schema_match is True


def test_preflight_rejects_file_extension_content_mismatch(tmp_path: Path) -> None:
    source_file = tmp_path / "not-really.xlsx"
    source_file.write_text("机构名称\n医院甲\n", encoding="utf-8-sig")

    with pytest.raises(ValueError, match="format.*match"):
        inspect_open_data_file(source_file, BEIJING_HOSPITALS)
