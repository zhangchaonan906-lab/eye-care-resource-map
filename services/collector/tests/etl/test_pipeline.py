from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from eye_collector.etl.models import FacilityTarget, NormalizedRecord, SourceSnapshot
from eye_collector.etl.pipeline import Pipeline


class Repository:
    def __init__(
        self,
        snapshots: list[SourceSnapshot],
        *,
        facilities: list[FacilityTarget] | None = None,
        duplicate_ids: list[str] | None = None,
        already_processed: int = 0,
    ) -> None:
        self.snapshots = snapshots
        self.facilities = facilities or []
        self.duplicate_ids = duplicate_ids or []
        self.already_processed = already_processed
        self.created: list[tuple[str, tuple[Any, ...]]] = []
        self.matches: list[tuple[str, str, str | None]] = []
        self.duplicate_cases: list[tuple[tuple[str, ...], list[str]]] = []
        self.dispositions: list[tuple[str, str]] = []
        self.target_queries: list[NormalizedRecord] = []
        self.raw_before = [dict(snapshot.raw_payload) for snapshot in snapshots]
        self._counter = 0

    @contextmanager
    def atomic(self) -> Iterator[None]:
        yield

    def count_existing_candidates(self) -> int:
        return self.already_processed

    def fetch_pending(self, limit: int | None = None) -> list[SourceSnapshot]:
        return self.snapshots[:limit] if limit is not None else self.snapshots

    def insert_candidate(self, normalized: Any, evidence: tuple[Any, ...]) -> str:
        self._counter += 1
        candidate_id = f"candidate-{self._counter}"
        self.created.append((candidate_id, evidence))
        return candidate_id

    def facility_targets_for(self, candidate: NormalizedRecord) -> list[FacilityTarget]:
        self.target_queries.append(candidate)
        return self.facilities

    def record_terminal_skip(self, source_record_id: str, reason_code: str) -> None:
        self.dispositions.append((source_record_id, reason_code))

    def update_match(self, candidate_id: str, status: str, facility_id: str | None) -> None:
        self.matches.append((candidate_id, status, facility_id))

    def find_duplicate_candidate_ids(
        self, key: tuple[str, ...], *, exclude_candidate_id: str
    ) -> list[str]:
        return self.duplicate_ids

    def persist_duplicate_case(self, key: tuple[str, ...], candidate_ids: list[str]) -> str:
        self.duplicate_cases.append((key, candidate_ids))
        return "duplicate-case-1"


def snapshot(
    source_record_id: str, payload: dict[str, object], *, reliable: bool = False
) -> SourceSnapshot:
    return SourceSnapshot(source_record_id, payload, reliable)


def test_pipeline_parses_normalizes_extracts_evidence_and_returns_structured_counts() -> None:
    payload = {
        "name": "  示例综合医院（东院） ",
        "address": "北京市朝阳区测试路 1 号",
        "phone": "010-12345678",
        "administrative_code": "110105",
        "campus_name": "东院",
        "departments": ["内科", "眼科门诊"],
    }
    repository = Repository(
        [snapshot("source-1", payload)],
        facilities=[FacilityTarget("facility-1", "示例综合医院(东院)", "东院", "110105", None)],
    )

    result = Pipeline(repository).run()

    assert result.as_dict() == {
        "source_records_read": 1,
        "candidates_created": 1,
        "already_processed": 0,
        "skipped": 0,
        "evidence_created": 1,
        "matched": 1,
        "needs_review": 0,
        "duplicate_cases": 0,
        "errors": 0,
    }
    assert repository.created[0][1][0].evidence_text == "眼科门诊"
    assert repository.matches == [("candidate-1", "matched", "facility-1")]
    assert repository.target_queries[0].source_record_id == "source-1"
    assert payload == repository.raw_before[0]


def test_pipeline_queues_exact_duplicate_candidates_for_review() -> None:
    repository = Repository(
        [
            snapshot(
                "source-1",
                {"name": "样例医院", "administrative_code": "110105"},
            )
        ],
        duplicate_ids=["candidate-existing"],
    )

    result = Pipeline(repository).run()

    assert result.needs_review == 1
    assert result.duplicate_cases == 1
    assert repository.matches == []
    assert repository.duplicate_cases == [
        (("name_region_campus", "样例医院", "110105", ""), ["candidate-1", "candidate-existing"])
    ]


def test_pipeline_sends_same_name_without_region_code_to_review_not_merge() -> None:
    repository = Repository(
        [snapshot("source-1", {"name": "宝安测试医院"})],
        duplicate_ids=["candidate-from-another-snapshot"],
    )

    result = Pipeline(repository).run()

    assert result.needs_review == 1
    assert result.duplicate_cases == 1
    assert repository.duplicate_cases == [
        (
            ("name_only", "宝安测试医院", ""),
            ["candidate-1", "candidate-from-another-snapshot"],
        )
    ]
    assert repository.matches == []


def test_pipeline_counts_invalid_and_previously_processed_snapshots() -> None:
    repository = Repository(
        [snapshot("bad-name", {"address": "北京市某路"})],
        already_processed=4,
    )

    result = Pipeline(repository).run()

    assert result.already_processed == 4
    assert result.skipped == 1
    assert result.candidates_created == 0
    assert repository.dispositions == [("bad-name", "missing_name")]


@pytest.mark.parametrize("placeholder", ["-", "—"])
def test_placeholder_names_are_terminally_skipped_without_removing_raw_snapshot(
    placeholder: str,
) -> None:
    raw_payload = {"name": placeholder, "address": "宝安区测试路"}
    repository = Repository([snapshot("source-row-1", raw_payload)])

    result = Pipeline(repository).run()

    assert result.skipped == 1
    assert result.candidates_created == 0
    assert repository.created == []
    assert repository.dispositions == [("source-row-1", "invalid_name_placeholder")]
    assert raw_payload == repository.raw_before[0]
