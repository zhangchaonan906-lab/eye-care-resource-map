from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eye_collector.geocoding.models import ProviderPolicy
from eye_collector.geocoding.repository import GeocodeRepository


@dataclass
class Cursor:
    rows: list[tuple[Any, ...]]

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None


class Connection:
    def __init__(self, responses: list[list[tuple[Any, ...]]]) -> None:
        self.responses = responses
        self.statements: list[tuple[str, tuple[Any, ...] | None]] = []

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Cursor:
        self.statements.append((query, params))
        return Cursor(self.responses.pop(0))


def test_fetch_pending_is_scoped_to_provider_and_skips_stored_query() -> None:
    connection = Connection(
        [[("candidate-1", "source-1", "synthetic address", "normalized address", "110105")]]
    )
    repository = GeocodeRepository(connection)  # type: ignore[arg-type]

    rows = repository.fetch_pending(ProviderPolicy("fixture", "fixture-v1", True, 10), limit=3)

    query, params = connection.statements[0]
    assert len(rows) == 1
    assert rows[0].source_record_id == "source-1"
    assert "NOT EXISTS" in query
    assert "prior.candidate_record_id = cr.id" in query
    assert "prior.query_address" in query
    assert "prior.provider_version = %s" in query
    assert "ORDER BY cr.processed_at, cr.id" in query
    assert params == (None, None, "fixture", "fixture-v1", 3)


def test_database_policy_is_the_source_of_provider_quota_and_storage_gate() -> None:
    connection = Connection([[(False, 25, 0.5)]])
    repository = GeocodeRepository(connection)  # type: ignore[arg-type]

    policy = repository.approved_policy("fixture", "fixture-v1")

    assert policy == ProviderPolicy("fixture", "fixture-v1", False, 25, 0.5)
    assert connection.statements[0][1] == ("fixture", "fixture-v1")


def test_fetch_pending_can_scope_to_one_candidate() -> None:
    connection = Connection([[]])
    repository = GeocodeRepository(connection)  # type: ignore[arg-type]

    repository.fetch_pending(
        ProviderPolicy("fixture", "fixture-v1", True, 10),
        candidate_record_id="123e4567-e89b-12d3-a456-426614174000",
    )

    query, params = connection.statements[0]
    assert "cr.id = %s::uuid" in query
    assert params == (
        "123e4567-e89b-12d3-a456-426614174000",
        "123e4567-e89b-12d3-a456-426614174000",
        "fixture",
        "fixture-v1",
        None,
    )
