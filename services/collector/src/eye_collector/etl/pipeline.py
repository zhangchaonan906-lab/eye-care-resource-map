from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Protocol

from eye_collector.etl.evidence import extract_ophthalmology_evidence
from eye_collector.etl.matching import duplicate_key, match_facility
from eye_collector.etl.models import (
    FacilityTarget,
    NormalizedRecord,
    OphthalmologyEvidence,
    PipelineStats,
    SourceSnapshot,
)
from eye_collector.etl.normalization import normalize_record
from eye_collector.etl.parser import parse_snapshot


class PipelineRepository(Protocol):
    def atomic(self) -> AbstractContextManager[None]: ...

    def fetch_pending(self, limit: int | None = None) -> list[SourceSnapshot]: ...

    def count_existing_candidates(self) -> int: ...

    def insert_candidate(
        self,
        normalized: NormalizedRecord,
        evidence: tuple[OphthalmologyEvidence, ...],
    ) -> str | None: ...

    def facility_targets(self) -> list[FacilityTarget]: ...

    def update_match(
        self, candidate_id: str, status: str, facility_id: str | None
    ) -> None: ...

    def find_duplicate_candidate_ids(
        self, key: tuple[str, ...], *, exclude_candidate_id: str
    ) -> list[str]: ...

    def persist_duplicate_case(self, key: tuple[str, ...], candidate_ids: list[str]) -> str: ...


class Pipeline:
    def __init__(
        self,
        repository: PipelineRepository,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger("eye_collector.etl")

    def run(self, *, limit: int | None = None) -> PipelineStats:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")

        snapshots = self._repository.fetch_pending(limit)
        counts = {
            "source_records_read": len(snapshots),
            "candidates_created": 0,
            "already_processed": self._repository.count_existing_candidates(),
            "skipped": 0,
            "evidence_created": 0,
            "matched": 0,
            "needs_review": 0,
            "duplicate_cases": 0,
            "errors": 0,
        }

        for snapshot in snapshots:
            try:
                self._process_snapshot(snapshot, counts)
            except Exception as error:
                counts["errors"] += 1
                self._logger.warning(
                    "etl_record_failed",
                    extra={
                        "event": "etl_record_failed",
                        "source_record_id": snapshot.source_record_id,
                        "error_type": type(error).__name__,
                    },
                )

        self._logger.info("etl_completed", extra={"event": "etl_completed", **counts})
        return PipelineStats(**counts)

    def _process_snapshot(self, snapshot: SourceSnapshot, counts: dict[str, int]) -> None:
        parsed = parse_snapshot(
            snapshot.source_record_id,
            snapshot.raw_payload,
            registration_id_reliable=snapshot.registration_id_reliable,
        )
        if parsed.record is None:
            counts["skipped"] += 1
            return

        normalized = normalize_record(parsed.record)
        extraction = extract_ophthalmology_evidence(parsed.record)
        candidate_id: str | None = None
        duplicate = False
        with self._repository.atomic():
            candidate_id = self._repository.insert_candidate(
                normalized, extraction.evidence
            )
            if candidate_id is None:
                counts["already_processed"] += 1
                return

            match = match_facility(normalized, self._repository.facility_targets())
            key = duplicate_key(normalized)
            if key is not None:
                existing_ids = self._repository.find_duplicate_candidate_ids(
                    key, exclude_candidate_id=candidate_id
                )
                if existing_ids:
                    self._repository.persist_duplicate_case(
                        key, [candidate_id, *existing_ids]
                    )
                    duplicate = True

            if not duplicate:
                self._repository.update_match(
                    candidate_id, match.status, match.facility_id
                )

        counts["candidates_created"] += 1
        counts["evidence_created"] += len(extraction.evidence)
        if duplicate:
            counts["duplicate_cases"] += 1
            counts["needs_review"] += 1
        elif match.status == "matched":
            counts["matched"] += 1
        elif match.status == "needs_review":
            counts["needs_review"] += 1
