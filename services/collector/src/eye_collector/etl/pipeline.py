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
from eye_collector.logging_utils import safe_error_summary


class PipelineRepository(Protocol):
    def atomic(self) -> AbstractContextManager[None]: ...

    def fetch_pending(
        self, limit: int | None = None, *, import_run_id: str | None = None
    ) -> list[SourceSnapshot]: ...

    def count_existing_candidates(self, *, import_run_id: str | None = None) -> int: ...

    def insert_candidate(
        self,
        normalized: NormalizedRecord,
        evidence: tuple[OphthalmologyEvidence, ...],
    ) -> str | None: ...

    def facility_targets_for(self, candidate: NormalizedRecord) -> list[FacilityTarget]: ...

    def record_terminal_skip(self, source_record_id: str, reason_code: str) -> None: ...

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

    def run(
        self, *, limit: int | None = None, import_run_id: str | None = None
    ) -> PipelineStats:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")

        snapshots = self._repository.fetch_pending(limit, import_run_id=import_run_id)
        counts = {
            "source_records_read": len(snapshots),
            "candidates_created": 0,
            "already_processed": self._repository.count_existing_candidates(
                import_run_id=import_run_id
            ),
            "skipped": 0,
            "evidence_created": 0,
            "matched": 0,
            "needs_review": 0,
            "duplicate_cases": 0,
            "errors": 0,
        }

        duplicate_case_ids: set[str] = set()
        for snapshot in snapshots:
            try:
                duplicate_case_id = self._process_snapshot(snapshot, counts)
                if duplicate_case_id is not None:
                    duplicate_case_ids.add(duplicate_case_id)
            except Exception as error:
                counts["errors"] += 1
                self._logger.warning(
                    "etl_record_failed",
                    extra={
                        "event": "etl_record_failed",
                        "source_record_id": snapshot.source_record_id,
                        "error_type": type(error).__name__,
                        "error": safe_error_summary(error),
                    },
                )

        counts["duplicate_cases"] = len(duplicate_case_ids)
        self._logger.info("etl_completed", extra={"event": "etl_completed", **counts})
        return PipelineStats(**counts)

    def _process_snapshot(
        self, snapshot: SourceSnapshot, counts: dict[str, int]
    ) -> str | None:
        parsed = parse_snapshot(
            snapshot.source_record_id,
            snapshot.raw_payload,
            registration_id_reliable=snapshot.registration_id_reliable,
        )
        if parsed.record is None:
            with self._repository.atomic():
                self._repository.record_terminal_skip(
                    snapshot.source_record_id, parsed.skip_reason or "missing_name"
                )
            counts["skipped"] += 1
            return None

        normalized = normalize_record(parsed.record)
        extraction = extract_ophthalmology_evidence(parsed.record)
        candidate_id: str | None = None
        duplicate_case_id: str | None = None
        with self._repository.atomic():
            candidate_id = self._repository.insert_candidate(
                normalized, extraction.evidence
            )
            if candidate_id is None:
                counts["already_processed"] += 1
                return None

            match = match_facility(
                normalized, self._repository.facility_targets_for(normalized)
            )
            key = duplicate_key(normalized)
            if key is not None:
                existing_ids = self._repository.find_duplicate_candidate_ids(
                    key, exclude_candidate_id=candidate_id
                )
                if existing_ids:
                    duplicate_case_id = self._repository.persist_duplicate_case(
                        key, [candidate_id, *existing_ids]
                    )

            if duplicate_case_id is None:
                self._repository.update_match(
                    candidate_id, match.status, match.facility_id
                )

        counts["candidates_created"] += 1
        counts["evidence_created"] += len(extraction.evidence)
        if duplicate_case_id is not None:
            counts["needs_review"] += 1
        elif match.status == "matched":
            counts["matched"] += 1
        elif match.status == "needs_review":
            counts["needs_review"] += 1
        return duplicate_case_id
