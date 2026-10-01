from __future__ import annotations

import csv
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eye_collector.hashing import canonical_sha256
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage
from eye_collector.sources.base import SourceAdapter

_MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_RECORDS_PER_RUN = 150


@dataclass(frozen=True, slots=True)
class OpenDataDataset:
    source_key: str
    source_name: str
    dataset_url: str
    expected_headers: tuple[str, ...]
    field_mapping: tuple[tuple[str, str], ...]
    stable_key_header: str | None = None

    def __post_init__(self) -> None:
        raw_headers = [header for header, _canonical in self.field_mapping]
        if len(raw_headers) != len(set(raw_headers)):
            raise ValueError("field mapping contains duplicate source headers")
        if not set(raw_headers).issubset(self.expected_headers):
            raise ValueError("mapped source headers must be in expected_headers")
        if (
            self.stable_key_header is not None
            and self.stable_key_header not in self.expected_headers
        ):
            raise ValueError("stable_key_header must be in expected_headers")
        if not self.dataset_url.startswith("https://"):
            raise ValueError("dataset_url must use HTTPS")


BEIJING_HOSPITALS = OpenDataDataset(
    source_key="beijing-open-data-hospitals",
    source_name="北京市公共数据开放平台-医院",
    dataset_url="https://data.beijing.gov.cn/zyml/wnkfsj/5652.htm",
    expected_headers=("机构名称",),
    field_mapping=(("机构名称", "name"),),
    stable_key_header="机构名称",
)

BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS = OpenDataDataset(
    source_key="beijing-open-data-designated-medical-institutions",
    source_name="北京市公共数据开放平台-定点医疗机构信息",
    dataset_url="https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm",
    expected_headers=("医院地址", "医院等级", "医院类别", "所属区", "定点医疗机构编码", "医院名称"),
    field_mapping=(
        ("医院名称", "name"),
        ("医院地址", "address"),
        ("所属区", "administrative_context"),
        ("医院等级", "hospital_grade"),
        ("医院类别", "source_category"),
        ("定点医疗机构编码", "registration_id"),
    ),
    stable_key_header="定点医疗机构编码",
)

SHENZHEN_BAOAN_HOSPITALS = OpenDataDataset(
    source_key="shenzhen-open-data-baoan-hospital-basic-information",
    source_name="深圳市政府数据开放平台-宝安区-医院基本信息",
    dataset_url="https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636",
    expected_headers=(
        "ID",
        "NAME",
        "LOCAL",
        "MANAGER",
        "ADDRESS",
        "CODE",
        "PHONE",
        "EMAIL",
        "WEBURL",
        "PROPERTY",
        "LEVELS",
        "STEP",
        "YESONO",
        "HOSPITALDESC",
        "HONOR",
        "ADVANTAGE",
        "TRAFFIC",
    ),
    field_mapping=(
        ("ID", "source_reference_id"),
        ("NAME", "name"),
        ("LOCAL", "administrative_context"),
        ("ADDRESS", "address"),
        ("LEVELS", "hospital_level"),
        ("STEP", "hospital_grade"),
        ("PROPERTY", "source_category"),
        ("ADVANTAGE", "specialties"),
    ),
    stable_key_header="ID",
)


class OpenDataFileAdapter(SourceAdapter):
    """Read an operator-downloaded official CSV/XLS/XLSX without making network calls."""

    def __init__(self, path: str | Path, dataset: OpenDataDataset) -> None:
        self._path = Path(path)
        self._dataset = dataset
        if self._path.suffix.lower() not in {".csv", ".xls", ".xlsx"}:
            raise ValueError("supported formats are CSV, XLS, and XLSX")
        if not self._path.is_file():
            raise ValueError("source file does not exist")
        if self._path.stat().st_size > _MAX_FILE_BYTES:
            raise ValueError("source file size exceeds the 10 MiB limit")

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            source_key=self._dataset.source_key,
            source_name=self._dataset.source_name,
            catalog_url=self._dataset.dataset_url,
            access_method="file",
        )

    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        if cursor is not None:
            raise ValueError("file adapter does not support pagination")
        if len(region_code) != 6 or not region_code.isdigit():
            raise ValueError("region_code must contain six digits")
        return SourcePage(self._read_records(_MAX_RECORDS_PER_RUN), None)

    def iter_pages(
        self,
        region_code: str,
        limit: int | None = None,
        *,
        on_request: Callable[[], None] | None = None,
    ) -> Iterator[SourcePage]:
        if limit is None:
            raise ValueError("official file imports require an explicit record limit")
        if limit > _MAX_RECORDS_PER_RUN:
            raise ValueError("official file imports are limited to 150 records per run")
        if len(region_code) != 6 or not region_code.isdigit():
            raise ValueError("region_code must contain six digits")
        if limit < 1:
            raise ValueError("limit must be a positive integer")
        if on_request is not None:
            on_request()
        yield SourcePage(self._read_records(limit), None)

    def _read_records(self, limit: int) -> tuple[RawRecord, ...]:
        suffix = self._path.suffix.lower()
        if suffix == ".csv":
            rows = self._read_csv(limit)
        elif suffix == ".xlsx":
            rows = self._read_xlsx(limit)
        else:
            rows = self._read_xls(limit)

        records: list[RawRecord] = []
        for row in rows:
            if all(value is None or value == "" for value in row.values()):
                continue
            source_fields = {
                header: _string_value(row[header]) for header, _name in self._dataset.field_mapping
            }
            mapped = {
                canonical_name: source_fields[source_header]
                for source_header, canonical_name in self._dataset.field_mapping
                if source_fields[source_header] is not None
            }
            name = mapped.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("source row is missing a required hospital name")
            stable_value = row.get(self._dataset.stable_key_header or "")
            source_key = _string_value(stable_value)
            if not source_key:
                source_key = canonical_sha256(source_fields)
            payload: dict[str, Any] = {"source_fields": source_fields, **mapped}
            records.append(RawRecord(source_key, self._dataset.dataset_url, payload))
            if len(records) >= limit:
                break
        return tuple(records)

    def _read_csv(self, limit: int) -> list[dict[str, object]]:
        with self._path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            self._validate_headers(reader.fieldnames)
            rows: list[dict[str, object]] = []
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("source file row width does not match its approved headers")
                if all(value is None or value == "" for value in row.values()):
                    continue
                rows.append(dict(row))
                if len(rows) >= limit:
                    break
            return rows

    def _read_xlsx(self, limit: int) -> list[dict[str, object]]:
        from openpyxl import load_workbook  # type: ignore[import-untyped]

        workbook = load_workbook(self._path, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            row_iter = sheet.iter_rows(values_only=True)
            headers = next(row_iter, None)
            names = self._validate_headers(headers)
            rows: list[dict[str, object]] = []
            for values in row_iter:
                if all(value is None or value == "" for value in values):
                    continue
                rows.append(dict(zip(names, values, strict=True)))
                if len(rows) >= limit:
                    break
            return rows
        finally:
            workbook.close()

    def _read_xls(self, limit: int) -> list[dict[str, object]]:
        import xlrd  # type: ignore[import-untyped]

        workbook = xlrd.open_workbook(self._path, on_demand=True)
        try:
            sheet = workbook.sheet_by_index(0)
            if sheet.nrows == 0:
                raise ValueError("source file header schema is missing")
            headers = self._validate_headers(sheet.row_values(0))
            rows: list[dict[str, object]] = []
            for row_index in range(1, sheet.nrows):
                row: dict[str, object] = {}
                for column_index, header in enumerate(headers):
                    cell = sheet.cell(row_index, column_index)
                    if (
                        header == self._dataset.stable_key_header
                        and cell.ctype == xlrd.XL_CELL_NUMBER
                    ):
                        workbook.release_resources()
                        raise ValueError("numeric stable IDs in XLS are ambiguous; use CSV/XLSX")
                    row[header] = cell.value
                if all(value is None or value == "" for value in row.values()):
                    continue
                rows.append(row)
                if len(rows) >= limit:
                    break
            return rows
        finally:
            workbook.release_resources()

    def _validate_headers(self, headers: Sequence[object] | None) -> list[str]:
        if headers is None or any(header is None for header in headers):
            raise ValueError("source file header schema is missing")
        actual = [str(header) for header in headers]
        if len(actual) != len(set(actual)) or set(actual) != set(self._dataset.expected_headers):
            raise ValueError(
                "source file header schema does not match the approved dataset mapping"
            )
        return actual


def _string_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value)
    return text if text else None
