from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from eye_collector.cli import build_parser, main
from eye_collector.models import RawRecord, SourceDescriptor, SourceRegistration
from eye_collector.policy import SourcePolicy
from eye_collector.sources.open_data_file import BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS


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

    def start_approved_run(
        self, descriptor: SourceDescriptor, region_code: str, policy: SourcePolicy
    ) -> tuple[str, SourceRegistration]:
        policy.authorize(self.registration, access_method=descriptor.access_method)
        return "cli-run-id", self.registration

    def snapshot_exists(self, source_id: str, record: RawRecord, content_hash: str) -> bool:
        return (record.source_key, content_hash) in self.records

    def insert_snapshot(
        self, run_id: str, source_id: str, record: RawRecord, content_hash: str
    ) -> bool:
        marker = (record.source_key, content_hash)
        if marker in self.records:
            return False
        self.records.add(marker)
        self.inserted += 1
        return True

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
            "医院名称": "北京市测试医院",
            "医院地址": "北京市测试路1号",
            "医院等级": "三级甲等",
            "医院类别": "综合",
            "所属区": "东城区",
            "定点医疗机构编码": "01020304",
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
                "administrative_context",
                "hospital_grade",
                "source_category",
                "registration_id",
            }
        ),
        "manual_only",
        "approved",
    )
    monkeypatch.setenv("PILOT_REAL_DATA", "true")
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
