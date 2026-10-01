from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from eye_collector.db import PostgresRepository
from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import RawRecord, SourceDescriptor
from eye_collector.policy import SourcePolicy


@dataclass
class FakeCursor:
    rows: list[tuple[Any, ...]]

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, responses: list[list[tuple[Any, ...]]]) -> None:
        self.responses = responses
        self.statements: list[tuple[str, tuple[Any, ...] | None]] = []
        self.transactions = 0

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.transactions += 1
        yield

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> FakeCursor:
        self.statements.append((query, params))
        if "SET TRANSACTION" in query:
            return FakeCursor([])
        return FakeCursor(self.responses.pop(0))


@pytest.fixture
def descriptor() -> SourceDescriptor:
    return SourceDescriptor("fixture", "Fixture Directory", "https://fixture.invalid/directory")


def source_row(status: str = "approved") -> tuple[Any, ...]:
    return (
        "00000000-0000-0000-0000-000000000001",
        "Fixture Directory",
        "https://fixture.invalid/directory",
        "Synthetic local fixture",
        ["name", "address"],
        "automated_access_allowed",
        status,
        None,
        None,
        None,
        0,
    )


def test_pending_source_is_rejected_before_import_run_insert(
    descriptor: SourceDescriptor,
) -> None:
    connection = FakeConnection([[source_row("pending")]])
    repository = PostgresRepository(connection)  # type: ignore[arg-type]

    with pytest.raises(SourcePolicyError, match="approved"):
        repository.start_approved_run(descriptor, "110000", SourcePolicy())

    assert len(connection.statements) == 2
    assert all(
        "INSERT INTO app_private.import_runs" not in query for query, _ in connection.statements
    )


def test_unknown_source_is_rejected_before_import_run_insert(
    descriptor: SourceDescriptor,
) -> None:
    connection = FakeConnection([[]])
    repository = PostgresRepository(connection)  # type: ignore[arg-type]

    with pytest.raises(SourcePolicyError, match="not registered"):
        repository.start_approved_run(descriptor, "110000", SourcePolicy())

    assert len(connection.statements) == 2


def test_approved_source_is_locked_and_run_created_in_same_transaction(
    descriptor: SourceDescriptor,
) -> None:
    connection = FakeConnection([[source_row()], [("run-id",)]])
    repository = PostgresRepository(connection)  # type: ignore[arg-type]

    run_id, source = repository.start_approved_run(descriptor, "110000", SourcePolicy())

    assert run_id == "run-id"
    assert source.status == "approved"
    assert connection.transactions == 1
    assert "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE" in connection.statements[0][0]
    assert "INSERT INTO app_private.import_runs" in connection.statements[2][0]
    assert "FROM app_private.source_catalog" in connection.statements[2][0]
    assert "status = 'approved'" in connection.statements[2][0]
    assert connection.statements[2][1] == ("110000", source.id)


def test_ambiguous_source_is_rejected_before_import_run_insert(
    descriptor: SourceDescriptor,
) -> None:
    connection = FakeConnection([[source_row(), source_row()]])
    repository = PostgresRepository(connection)  # type: ignore[arg-type]

    with pytest.raises(SourcePolicyError, match="ambiguous"):
        repository.start_approved_run(descriptor, "110000", SourcePolicy())

    assert len(connection.statements) == 2


def test_snapshot_insert_uses_conflict_key_and_returns_inserted_state() -> None:
    connection = FakeConnection([[("new-snapshot-id",)]])
    repository = PostgresRepository(connection)  # type: ignore[arg-type]
    record = RawRecord("facility-1", "https://fixture.invalid/1", {"name": "Fixture"})

    inserted = repository.insert_snapshot("run-id", "source-id", record, "a" * 64)

    assert inserted is True
    query, params = connection.statements[0]
    assert "ON CONFLICT (source_id, source_key, content_hash) DO NOTHING" in query
    assert params is not None
    assert params[0:2] == ("source-id", "facility-1")
