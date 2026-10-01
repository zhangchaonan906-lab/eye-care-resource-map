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

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows


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


def test_terminal_missing_name_skip_is_versioned_and_idempotent() -> None:
    connection = Connection([])
    repository = ETLRepository(connection)  # type: ignore[arg-type]

    repository.record_terminal_skip("source-record-1", "missing_name")

    query, params = connection.statements[0]
    assert "etl_source_dispositions" in query
    assert "ON CONFLICT (source_record_id, pipeline_version) DO NOTHING" in query
    assert params == ("source-record-1", "p3.2", "terminal_skip", "missing_name")


def test_facility_target_query_filters_to_reliable_registration_or_exact_name_region() -> None:
    connection = Connection(
        [("facility-1", "示例医院", "东院", "110105", "REG-1")]
    )
    repository = ETLRepository(connection)  # type: ignore[arg-type]

    targets = repository.facility_targets_for(candidate())

    query, params = connection.statements[0]
    assert len(targets) == 1
    assert "o.registration_id = %s" in query
    assert "f.normalized_name = %s" in query
    assert "r.adcode = %s" in query
    assert params == ("REG-1", "REG-1", "110105", "示例医院(东院)")


def test_untrusted_registration_id_is_not_queried() -> None:
    connection = Connection([])
    repository = ETLRepository(connection)  # type: ignore[arg-type]
    untrusted = candidate()
    untrusted = NormalizedRecord(
        **{
            field: getattr(untrusted, field)
            for field in untrusted.__dataclass_fields__
            if field != "registration_id_reliable"
        },
        registration_id_reliable=False,
    )

    repository.facility_targets_for(untrusted)

    query, params = connection.statements[0]
    assert "o.registration_id = %s" in query
    assert params == (None, None, "110105", "示例医院(东院)")


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
    assert "ON CONFLICT (match_fingerprint)" in connection.statements[0][0]
    assert "WHERE match_fingerprint IS NOT NULL DO NOTHING" in connection.statements[0][0]
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
