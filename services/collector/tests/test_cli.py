from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook

from eye_collector.changes import ChangeType
from eye_collector.cli import build_parser, main
from eye_collector.models import (
    RawRecord,
    SnapshotWriteResult,
    SourceDescriptor,
    SourceRegistration,
)
from eye_collector.policy import SourcePolicy
from eye_collector.sources.open_data_file import (
    BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS,
    SHENZHEN_BAOAN_HOSPITALS,
)


class FakeRepository:
    def __init__(self) -> None:
        self.registration = SourceRegistration(
            "source-id",
            "Fixture Directory",
            "https://fixture.invalid/directory",
            "Synthetic local fixture",
            frozenset(
                {
                    "name",
                    "address",
                    "phone",
                    "region",
                    "administrative_code",
                    "registration_id",
                    "campus_name",
                    "departments",
                    "updated_at",
                }
            ),
            "automated_access_allowed",
            "approved",
        )
        self.records: set[tuple[str, str]] = set()
        self.inserted = 0
        self.final_status: str | None = None
        self.started = 0
        self.inspection_reads = 0

    def inspect_source(self, descriptor: SourceDescriptor) -> SourceRegistration | None:
        self.inspection_reads += 1
        if self.registration.name == descriptor.source_name:
            return self.registration
        return None

    def start_approved_run(
        self, descriptor: SourceDescriptor, region_code: str, policy: SourcePolicy
    ) -> tuple[str, SourceRegistration]:
        policy.authorize(self.registration, access_method=descriptor.access_method)
        self.started += 1
        return "cli-run-id", self.registration

    def start_approved_file_run(
        self,
        descriptor: SourceDescriptor,
        region_code: str,
        policy: SourcePolicy,
        provenance: object,
    ) -> tuple[str, SourceRegistration]:
        policy.authorize(self.registration, access_method=descriptor.access_method)
        self.started += 1
        return "cli-run-id", self.registration

    def snapshot_exists(self, source_id: str, record: RawRecord, content_hash: str) -> bool:
        return (record.source_key, content_hash) in self.records

    def preview_snapshot(
        self, source_id: str, record: RawRecord, content_hash: str
    ) -> SnapshotWriteResult:
        if (record.source_key, content_hash) in self.records:
            return SnapshotWriteResult(ChangeType.UNCHANGED)
        return SnapshotWriteResult(ChangeType.NEW)

    def insert_snapshot(
        self, run_id: str, source_id: str, record: RawRecord, content_hash: str
    ) -> SnapshotWriteResult:
        marker = (record.source_key, content_hash)
        if marker in self.records:
            return SnapshotWriteResult(ChangeType.UNCHANGED)
        self.records.add(marker)
        self.inserted += 1
        return SnapshotWriteResult(ChangeType.NEW, f"synthetic-{self.inserted}")

    def finish_run(
        self, run_id: str, status: str, counts: dict[str, int], error_summary: str | None = None
    ) -> None:
        self.final_status = status

    def close(self) -> None:
        return None


def test_cli_parser_accepts_source_region_limit_and_dry_run() -> None:
    args = build_parser().parse_args(
        ["run", "--source", "fixture", "--region", "110000", "--limit", "3", "--dry-run"]
    )

    assert args.source == "fixture"
    assert args.region == "110000"
    assert args.limit == 3
    assert args.dry_run is True


@pytest.mark.parametrize(
    ("argv", "command", "loop"),
    [
        (["scheduler", "--once"], "scheduler", False),
        (["worker", "--once"], "worker", False),
        (["worker", "--loop", "--poll-seconds", "7"], "worker", True),
    ],
)
def test_cli_parser_exposes_scheduler_and_worker_modes(
    argv: list[str], command: str, loop: bool
) -> None:
    args = build_parser().parse_args(argv)

    assert args.command == command
    if command == "worker":
        assert args.loop is loop


def test_cli_parser_accepts_bounded_open_data_file_source() -> None:
    args = build_parser().parse_args(
        [
            "run",
            "--source",
            "beijing-open-data-designated-medical-institutions",
            "--region",
            "110000",
            "--file",
            "official.csv",
            "--limit",
            "100",
        ]
    )

    assert args.source == "beijing-open-data-designated-medical-institutions"
    assert args.file == "official.csv"
    assert args.limit == 100


def test_official_file_cli_uses_catalog_policy_and_existing_import_lifecycle(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    dataset = BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS
    source_file = tmp_path / "designated.csv"
    with source_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(dataset.expected_headers)
        row = {
            "序号": "1",
            "医院名称": "北京市测试医院",
            "定点医疗机构编码": "01020304",
            "所属区": "110101",
            "医院类别": "01",
            "医院等级": "03",
            "医院地址": "北京市测试路1号",
            "数据唯一记录号": "ignored-id",
            "数据创建时间": "created",
            "数据更新时间": "updated",
        }
        writer.writerow([row[header] for header in dataset.expected_headers])
    repository = FakeRepository()
    repository.registration = SourceRegistration(
        "source-id",
        dataset.source_name,
        dataset.dataset_url,
        "Official unconditional open dataset downloaded by the operator",
        frozenset(
            {
                "source_fields",
                "name",
                "address",
                "administrative_code",
                "hospital_grade",
                "source_category",
                "registration_id",
            }
        ),
        "manual_only",
        "approved",
    )
    monkeypatch.setenv("PILOT_REAL_DATA", "true")
    monkeypatch.setenv("PILOT_OPERATOR", "test-operator")
    monkeypatch.setenv("PILOT_FILE_OBTAINED_AT", "2026-10-01T10:00:00+08:00")
    monkeypatch.setenv("DATABASE_URL", "postgresql://eye_collector:test@localhost/eye")
    monkeypatch.setattr("eye_collector.cli.PostgresRepository.connect", lambda _url: repository)

    exit_code = main(
        [
            "run",
            "--source",
            dataset.source_key,
            "--region",
            "110000",
            "--file",
            str(source_file),
            "--limit",
            "1",
            "--dry-run",
        ]
    )

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["status"] == "succeeded"
    assert result["dry_run"] is True
    assert result["counts"]["inserted"] == 1
    assert repository.inserted == 0


def test_inspect_file_reports_readiness_without_starting_an_import_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    dataset = BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS
    source_file = tmp_path / "official.csv"
    with source_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(dataset.expected_headers)
        writer.writerow(
            [1, "测试医院", "12345", "110101", "01", "03", "地址", "x1", "created", "updated"]
        )
    repository = FakeRepository()
    repository.registration = SourceRegistration(
        "source-id",
        dataset.source_name,
        dataset.dataset_url,
        "official platform dataset",
        frozenset({"source_fields", "name", "address", "administrative_code"}),
        "manual_only",
        "approved",
        dataset_page=dataset.dataset_url,
        source_updated_at=date(2026, 8, 13),
        pilot_group_record_limit=300,
        pilot_group_record_count=0,
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://eye_collector:test@localhost/eye")
    monkeypatch.setattr("eye_collector.cli.PostgresRepository.connect", lambda _url: repository)

    exit_code = main(["inspect-file", "--source", dataset.source_key, "--file", str(source_file)])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["filename"] == "official.csv"
    assert result["file_size_bytes"] == source_file.stat().st_size
    assert result["detected_format"] == "csv"
    assert result["container_format"] is None
    assert result["headers"] == list(dataset.expected_headers)
    assert result["row_count"] == 1
    assert result["approved_dataset"] == dataset.source_name
    assert result["schema_match"] is True
    assert result["configured_pilot_limit"] == 300
    assert result["allowed_region"] == "110000"
    assert result["ready_to_import"] is True
    assert result["recommended_first_pilot_limit"] == 1
    assert repository.inspection_reads == 1
    assert repository.started == 0
    assert repository.inserted == 0


def test_inspect_zip_reports_original_and_member_fingerprints_read_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    dataset = SHENZHEN_BAOAN_HOSPITALS
    workbook = Workbook()
    workbook.active.title = "资源描述信息"
    data_sheet = workbook.create_sheet("数据集1")
    data_sheet.append(list(dataset.expected_headers))
    data_sheet.append(
        [
            "doc-1",
            "测试医院",
            "宝安区",
            "",
            "地址",
            "",
            "",
            "",
            "",
            "公立",
            "三级",
            "甲等",
            "",
            "有眼科门诊",
            "",
            "",
            "",
        ]
    )
    workbook_bytes = io.BytesIO()
    workbook.save(workbook_bytes)
    member_bytes = workbook_bytes.getvalue()
    source_file = tmp_path / "baoan.zip"
    member_name = "宝安区-医院基本信息_2920002800636.xlsx"
    with zipfile.ZipFile(source_file, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member_name, member_bytes)
    archive_bytes = source_file.read_bytes()

    repository = FakeRepository()
    repository.registration = SourceRegistration(
        "source-id",
        dataset.source_name,
        dataset.dataset_url,
        "approved synthetic fixture",
        frozenset(),
        "manual_only",
        "approved",
        dataset_page=dataset.dataset_url,
        source_updated_at=date(2025, 4, 15),
        pilot_group_record_limit=300,
        pilot_group_record_count=0,
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://eye_collector:test@localhost/eye")
    monkeypatch.setattr("eye_collector.cli.PostgresRepository.connect", lambda _url: repository)

    exit_code = main(["inspect-file", "--source", dataset.source_key, "--file", str(source_file)])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["filename"] == "baoan.zip"
    assert result["sha256"] == hashlib.sha256(archive_bytes).hexdigest()
    assert result["container_format"] == "zip"
    assert result["archive_member_name"] == member_name
    assert result["archive_member_sha256"] == hashlib.sha256(member_bytes).hexdigest()
    assert result["archive_member_size_bytes"] == len(member_bytes)
    assert result["data_sheet_name"] == "数据集1"
    assert result["row_count"] == 1
    assert result["ready_to_import"] is True
    assert result["recommended_first_pilot_limit"] == 1
    assert repository.inspection_reads == 1
    assert repository.started == 0
    assert repository.inserted == 0


def test_official_file_cli_requires_an_explicit_limit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PILOT_REAL_DATA", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://eye_collector:test@localhost/eye")

    exit_code = main(
        [
            "run",
            "--source",
            BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key,
            "--region",
            "110000",
            "--file",
            "missing.csv",
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "explicit --limit" in output.err
    assert output.out == ""


def test_cli_parser_accepts_fixture_geocode_dry_run() -> None:
    args = build_parser().parse_args(
        [
            "geocode",
            "--provider",
            "fixture",
            "--limit",
            "5",
            "--candidate-id",
            "123e4567-e89b-12d3-a456-426614174000",
            "--dry-run",
        ]
    )

    assert args.command == "geocode"
    assert args.provider == "fixture"
    assert args.limit == 5
    assert args.candidate_id == "123e4567-e89b-12d3-a456-426614174000"
    assert args.dry_run is True


def test_pilot_parser_requires_region_source_and_explicit_limit() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "pilot",
                "--source",
                BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key,
                "--region",
                "110000",
            ]
        )

    args = build_parser().parse_args(
        [
            "pilot",
            "--source",
            BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key,
            "--region",
            "110000",
            "--file",
            "official.csv",
            "--limit",
            "50",
            "--dry-run",
        ]
    )
    assert args.source == BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key
    assert args.region == "110000"
    assert args.limit == 50
    assert args.file == "official.csv"
    assert args.dry_run is True


def test_pilot_fails_closed_without_explicit_real_data_opt_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PILOT_REAL_DATA", raising=False)

    exit_code = main(
        [
            "pilot",
            "--source",
            BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key,
            "--region",
            "110000",
            "--file",
            "official.csv",
            "--limit",
            "50",
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "PILOT_REAL_DATA=true" in output.err
    assert output.out == ""


def test_pilot_uses_file_import_flow_after_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PILOT_REAL_DATA", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    exit_code = main(
        [
            "pilot",
            "--source",
            BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key,
            "--region",
            "110000",
            "--file",
            "official.csv",
            "--limit",
            "50",
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "DATABASE_URL" in output.err
    assert output.out == ""


def test_cli_fixture_dry_run_outputs_structured_stats(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = FakeRepository()
    monkeypatch.setenv("DATABASE_URL", "postgresql://eye_collector:test@localhost/eye")
    monkeypatch.setattr("eye_collector.cli.PostgresRepository.connect", lambda _url: repository)

    exit_code = main(
        ["run", "--source", "fixture", "--region", "110000", "--limit", "1", "--dry-run"]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["run_id"] == "cli-run-id"
    assert output["status"] == "succeeded"
    assert output["dry_run"] is True
    assert output["counts"]["requested"] == 1
    assert output["counts"]["received"] == 3
    assert output["counts"]["inserted"] == 1
    assert repository.inserted == 0
    assert repository.final_status == "succeeded"


def test_cli_fails_fast_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    exit_code = main(["run", "--source", "fixture", "--region", "110000"])

    output = capsys.readouterr()
    assert exit_code == 2
    assert "DATABASE_URL" in output.err
    assert output.out == ""
