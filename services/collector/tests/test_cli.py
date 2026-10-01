from __future__ import annotations

import json

import pytest

from eye_collector.cli import build_parser, main
from eye_collector.models import RawRecord, SourceDescriptor, SourceRegistration
from eye_collector.policy import SourcePolicy


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
        policy.authorize(self.registration)
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
        build_parser().parse_args(["pilot", "--source", "beijing-registry", "--region", "110000"])

    args = build_parser().parse_args(
        [
            "pilot",
            "--source",
            "beijing-registry",
            "--region",
            "110000",
            "--limit",
            "50",
            "--dry-run",
        ]
    )
    assert args.source == "beijing-registry"
    assert args.region == "110000"
    assert args.limit == 50
    assert args.dry_run is True


def test_pilot_fails_closed_without_explicit_real_data_opt_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PILOT_REAL_DATA", raising=False)

    exit_code = main(
        ["pilot", "--source", "beijing-registry", "--region", "110000", "--limit", "50"]
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "PILOT_REAL_DATA=true" in output.err
    assert output.out == ""


def test_pilot_stays_blocked_after_opt_in_when_source_gate_is_not_approved(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PILOT_REAL_DATA", "true")

    exit_code = main(
        ["pilot", "--source", "beijing-registry", "--region", "110000", "--limit", "50"]
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "P5-A source approval is incomplete" in output.err
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
