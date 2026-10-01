from __future__ import annotations

import json

import pytest

from eye_collector.cli import build_parser, main
from eye_collector.etl.models import PipelineStats


def test_process_command_accepts_limit() -> None:
    args = build_parser().parse_args(["process", "--limit", "5"])

    assert args.command == "process"
    assert args.limit == 5


def test_process_command_accepts_import_run_id() -> None:
    run_id = "b0a6264e-e125-4bbd-bf93-3da5ad8f13a1"
    args = build_parser().parse_args(["process", "--import-run-id", run_id])

    assert args.import_run_id == run_id


def test_process_command_uses_etl_login_and_emits_structured_stats(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FakePipeline:
        def __init__(self, repository: object) -> None:
            assert isinstance(repository, FakeRepository)

        def run(
            self,
            *,
            limit: int | None = None,
            import_run_id: str | None = None,
        ) -> PipelineStats:
            assert limit == 2
            assert import_run_id is None
            return PipelineStats(source_records_read=3, candidates_created=3)

    class FakeRepository:
        def close(self) -> None:
            return None

    monkeypatch.setenv("ETL_DATABASE_URL", "postgresql://eye_etl:test@localhost/eye")
    monkeypatch.setattr(
        "eye_collector.cli.ETLRepository.connect", lambda url: FakeRepository()
    )
    monkeypatch.setattr("eye_collector.cli.Pipeline", FakePipeline)

    exit_code = main(["process", "--limit", "2"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "source_records_read": 3,
        "candidates_created": 3,
        "already_processed": 0,
        "skipped": 0,
        "evidence_created": 0,
        "matched": 0,
        "needs_review": 0,
        "duplicate_cases": 0,
        "errors": 0,
    }


def test_process_command_requires_dedicated_etl_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ETL_DATABASE_URL", raising=False)

    assert main(["process"]) == 2
    assert "ETL_DATABASE_URL" in capsys.readouterr().err
