from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from eye_collector.etl.models import NormalizedRecord, OphthalmologyEvidence
from eye_collector.etl.repository import ETLRepository


@dataclass
class Cursor:
    rows: list[tuple[Any, ...]]

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None


class Connection:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.responses: list[list[tuple[Any, ...]]] = []
        self.statements: list[tuple[str, tuple[Any, ...] | None]] = []
        self.transactions = 0

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.transactions += 1
        yield

    def execute(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> Cursor:
        self.statements.append((query, params))
        rows = self.responses.pop(0) if self.responses else self.rows
        return Cursor(rows)


def candidate() -> NormalizedRecord:
    return NormalizedRecord(
        source_record_id="source-record-1",
        original_name="示例医院（东院）",
        normalized_name="示例医院(东院)",
        original_address="北京市朝阳区示例路1号",
        normalized_address="北京市朝阳区示例路1号",
        original_phone="010-12345678",
        normalized_phone="01012345678",
        administrative_code="110105",
        registration_id="REG-1",
        registration_id_reliable=True,
        campus_name="东院",
        raw_payload={
            "name": "示例医院（东院）",
            "ophthalmology_services": "眼科门诊",
        },
    )


def test_candidate_insert_is_parameterized_and_conflict_is_idempotent() -> None:
    connection = Connection([("candidate-id",)])
    repository = ETLRepository(connection)  # type: ignore[arg-type]
    evidence = (
        OphthalmologyEvidence("source-record-1", "ophthalmology_services", "眼科门诊"),
    )

    candidate_id = repository.insert_candidate(candidate(), evidence)

    assert candidate_id == "candidate-id"
    assert connection.transactions == 1
    assert len(connection.statements) == 2
    candidate_query, candidate_params = connection.statements[0]
    assert "ON CONFLICT (source_record_id) DO NOTHING" in candidate_query
    assert "RETURNING id::text" in candidate_query
    assert candidate_params is not None
    assert candidate_params[0] == "source-record-1"
    assert candidate_params[1].obj["name"] == "示例医院（东院）"
    assert candidate_params[2:8] == (
        "示例医院(东院)",
        "北京市朝阳区示例路1号",
        "01012345678",
        "110105",
        "REG-1",
        True,
    )
    evidence_query, evidence_params = connection.statements[1]
    assert "candidate_evidence" in evidence_query
    assert evidence_params is not None
    assert evidence_params[0:2] == ("candidate-id", "source-record-1")


def test_existing_source_record_candidate_skips_evidence_reinsertion() -> None:
    connection = Connection([])
    repository = ETLRepository(connection)  # type: ignore[arg-type]
    evidence = (
        OphthalmologyEvidence("source-record-1", "departments", "眼科"),
    )

    candidate_id = repository.insert_candidate(candidate(), evidence)

    assert candidate_id is None
    assert len(connection.statements) == 1


def test_duplicate_case_requires_two_distinct_candidate_ids() -> None:
    connection = Connection([])
    repository = ETLRepository(connection)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="at least two distinct"):
        repository.persist_duplicate_case(
            ("name_region_campus", "示例医院", "110105", ""), ["candidate-1"]
        )

    assert connection.statements == []


def test_duplicate_case_and_members_are_inserted_idempotently() -> None:
    connection = Connection([])
    connection.responses = [[("case-1",)], [], [], []]
    repository = ETLRepository(connection)  # type: ignore[arg-type]

    case_id = repository.persist_duplicate_case(
        ("name_region_campus", "示例医院", "110105", ""),
        ["candidate-1", "candidate-2"],
    )

    assert case_id == "case-1"
    assert connection.transactions == 1
    assert len(connection.statements) == 4
    assert "ON CONFLICT (match_fingerprint) DO NOTHING" in connection.statements[0][0]
    assert (
        "ON CONFLICT (duplicate_case_id, candidate_record_id) DO NOTHING"
        in connection.statements[1][0]
    )
    assert "needs_review" in connection.statements[3][0]


def test_existing_duplicate_case_is_reused_by_its_stable_fingerprint() -> None:
    connection = Connection([])
    connection.responses = [[], [("existing-case",)], [], [], []]
    repository = ETLRepository(connection)  # type: ignore[arg-type]

    case_id = repository.persist_duplicate_case(
        ("registration_id", "reg-9", "东院"), ["candidate-1", "candidate-2"]
    )

    assert case_id == "existing-case"
    assert "WHERE match_fingerprint = %s" in connection.statements[1][0]
