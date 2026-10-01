from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from eye_collector.etl.models import NormalizedRecord, OphthalmologyEvidence

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
            "registration_id": normalized.registration_id,
            "campus_name": normalized.campus_name,
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
