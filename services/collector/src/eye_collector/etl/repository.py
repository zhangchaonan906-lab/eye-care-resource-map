from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from eye_collector.etl.matching import duplicate_fingerprint, duplicate_reason
from eye_collector.etl.models import (
    FacilityTarget,
    NormalizedRecord,
    OphthalmologyEvidence,
    SourceSnapshot,
)

_PIPELINE_VERSION = "p3.1"
_EVIDENCE_RULE_VERSION = "ophthalmology-explicit-fields-v1"


class ETLRepository:
    """Persistence boundary for P3; deliberately has no facility write methods."""

    def __init__(self, connection: psycopg.Connection[tuple[Any, ...]]) -> None:
        self._connection = connection

    @classmethod
    def connect(cls, database_url: str) -> ETLRepository:
        return cls(psycopg.connect(database_url, row_factory=tuple_row, autocommit=True))

    def close(self) -> None:
        self._connection.close()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with self._connection.transaction():
            yield

    def fetch_pending(self, limit: int | None = None) -> list[SourceSnapshot]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._connection.execute(
            """
            SELECT sr.id::text, sr.raw_payload, sc.registration_id_reliable
            FROM app_private.source_records sr
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            WHERE sc.status = 'approved'
              AND sc.access_policy = 'automated_access_allowed'
              AND NOT EXISTS (
                SELECT 1 FROM app_private.candidate_records cr
                WHERE cr.source_record_id = sr.id
              )
            ORDER BY sr.collected_at, sr.id
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
        return [
            SourceSnapshot(str(row[0]), row[1], bool(row[2]))
            for row in rows
        ]

    def count_existing_candidates(self) -> int:
        row = self._connection.execute(
            """
            SELECT count(*)
            FROM app_private.source_records sr
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            JOIN app_private.candidate_records cr ON cr.source_record_id = sr.id
            WHERE sc.status = 'approved'
              AND sc.access_policy = 'automated_access_allowed'
            """
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def facility_targets(self) -> list[FacilityTarget]:
        rows = self._connection.execute(
            """
            SELECT f.id::text, f.name, f.campus_name, r.adcode, o.registration_id
            FROM app_private.facilities f
            JOIN app_private.regions r ON r.id = f.region_id
            LEFT JOIN app_private.organizations o ON o.id = f.organization_id
            WHERE f.verification_status <> 'withdrawn'
            ORDER BY f.id
            """
        ).fetchall()
        return [
            FacilityTarget(
                facility_id=str(row[0]),
                name=str(row[1]),
                campus_name=str(row[2]) if row[2] is not None else None,
                administrative_code=str(row[3]),
                registration_id=str(row[4]) if row[4] is not None else None,
            )
            for row in rows
        ]

    def find_duplicate_candidate_ids(
        self, key: tuple[str, ...], *, exclude_candidate_id: str
    ) -> list[str]:
        if key[0] == "registration_id" and len(key) == 3:
            rows = self._connection.execute(
                """
                SELECT id::text FROM app_private.candidate_records
                WHERE registration_id_reliable
                  AND registration_id = %s
                  AND campus_name IS NOT DISTINCT FROM NULLIF(%s, '')
                  AND match_status <> 'rejected'
                  AND id <> %s
                ORDER BY id
                """,
                (key[1], key[2], exclude_candidate_id),
            ).fetchall()
        elif key[0] == "name_region_campus" and len(key) == 4:
            rows = self._connection.execute(
                """
                SELECT id::text FROM app_private.candidate_records
                WHERE normalized_name = %s
                  AND administrative_code = %s
                  AND campus_name IS NOT DISTINCT FROM NULLIF(%s, '')
                  AND match_status <> 'rejected'
                  AND id <> %s
                ORDER BY id
                """,
                (key[1], key[2], key[3], exclude_candidate_id),
            ).fetchall()
        else:
            raise ValueError("invalid deterministic duplicate key")
        return [str(row[0]) for row in rows]

    def update_match(
        self, candidate_id: str, status: str, facility_id: str | None
    ) -> None:
        if status not in {"matched", "unmatched", "needs_review"}:
            raise ValueError("invalid deterministic match status")
        if (status == "matched") != (facility_id is not None):
            raise ValueError("only matched candidates may have a proposed facility")
        row = self._connection.execute(
            """
            UPDATE app_private.candidate_records
            SET match_status = %s, proposed_facility_id = %s
            WHERE id = %s AND match_status <> 'rejected'
            RETURNING id
            """,
            (status, facility_id, candidate_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("candidate was missing or rejected before matching")

    def insert_candidate(
        self,
        normalized: NormalizedRecord,
        evidence: tuple[OphthalmologyEvidence, ...],
    ) -> str | None:
        parsed_fields = {
            "name": normalized.original_name,
            "address": normalized.original_address,
            "phone": normalized.original_phone,
            "administrative_code": normalized.administrative_code,
            "registration_id": normalized.raw_payload.get("registration_id"),
            "campus_name": normalized.raw_payload.get("campus_name"),
            "ophthalmology_evidence_present": bool(evidence),
        }
        with self._connection.transaction():
            row = self._connection.execute(
                """
                INSERT INTO app_private.candidate_records (
                  source_record_id, parsed_fields, normalized_name, normalized_address,
                  normalized_phone, administrative_code, registration_id,
                  registration_id_reliable, campus_name, pipeline_version,
                  processed_at, match_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), 'unmatched')
                ON CONFLICT (source_record_id) DO NOTHING
                RETURNING id::text
                """,
                (
                    normalized.source_record_id,
                    Jsonb(parsed_fields),
                    normalized.normalized_name,
                    normalized.normalized_address,
                    normalized.normalized_phone,
                    normalized.administrative_code,
                    normalized.registration_id,
                    normalized.registration_id_reliable,
                    normalized.campus_name,
                    _PIPELINE_VERSION,
                ),
            ).fetchone()
            if row is None:
                return None

            candidate_id = str(row[0])
            for item in evidence:
                self._connection.execute(
                    """
                    INSERT INTO app_private.candidate_evidence (
                      candidate_record_id, source_record_id, field_name,
                      evidence_value, evidence_text, evidence_type, rule_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (candidate_record_id, field_name, evidence_text) DO NOTHING
                    """,
                    (
                        candidate_id,
                        normalized.source_record_id,
                        item.field_name,
                        Jsonb(normalized.raw_payload[item.field_name]),
                        item.evidence_text,
                        item.evidence_type,
                        _EVIDENCE_RULE_VERSION,
                    ),
                )
            return candidate_id

    def persist_duplicate_case(
        self, key: tuple[str, ...], candidate_ids: list[str]
    ) -> str:
        unique_ids = sorted(set(candidate_ids))
        if len(unique_ids) < 2:
            raise ValueError("duplicate case requires at least two distinct candidate ids")

        fingerprint = duplicate_fingerprint(key)
        reason = duplicate_reason(key)
        with self._connection.transaction():
            row = self._connection.execute(
                """
                INSERT INTO app_private.duplicate_cases (reason, match_fingerprint)
                VALUES (%s, %s)
                ON CONFLICT (match_fingerprint) DO NOTHING
                RETURNING id::text
                """,
                (reason, fingerprint),
            ).fetchone()
            if row is None:
                row = self._connection.execute(
                    """
                    SELECT id::text FROM app_private.duplicate_cases
                    WHERE match_fingerprint = %s
                    """,
                    (fingerprint,),
                ).fetchone()
            if row is None:
                raise RuntimeError("duplicate case could not be created or found")

            case_id = str(row[0])
            for candidate_id in unique_ids:
                self._connection.execute(
                    """
                    INSERT INTO app_private.duplicate_case_candidates
                      (duplicate_case_id, candidate_record_id)
                    VALUES (%s, %s)
                    ON CONFLICT (duplicate_case_id, candidate_record_id) DO NOTHING
                    """,
                    (case_id, candidate_id),
                )
            self._connection.execute(
                """
                UPDATE app_private.candidate_records
                SET match_status = 'needs_review', proposed_facility_id = NULL
                WHERE id = ANY(%s::uuid[]) AND match_status <> 'rejected'
                """,
                (unique_ids,),
            )
            return case_id
