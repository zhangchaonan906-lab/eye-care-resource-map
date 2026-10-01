from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from eye_collector.geocoding.models import (
    CoordinateValidation,
    GeocodeCandidate,
    GeocodeResult,
    ProviderPolicy,
)


class GeocodeRepository:
    """Least-privilege persistence adapter for candidate coordinate staging."""

    def __init__(self, connection: psycopg.Connection[tuple[Any, ...]]) -> None:
        self._connection = connection

    @classmethod
    def connect(cls, database_url: str) -> GeocodeRepository:
        return cls(psycopg.connect(database_url, row_factory=tuple_row, autocommit=True))

    def close(self) -> None:
        self._connection.close()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with self._connection.transaction():
            yield

    def fetch_pending(
        self,
        policy: ProviderPolicy,
        limit: int | None = None,
        candidate_record_id: str | None = None,
    ) -> list[GeocodeCandidate]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._connection.execute(
            """
            SELECT cr.id::text, cr.source_record_id::text,
              COALESCE(NULLIF(cr.parsed_fields->>'address', ''), cr.normalized_address, ''),
              cr.normalized_address, cr.administrative_code
            FROM app_private.candidate_records cr
            WHERE cr.match_status <> 'rejected'
              AND (%s::uuid IS NULL OR cr.id = %s::uuid)
              AND NOT EXISTS (
                SELECT 1 FROM app_private.candidate_locations prior
                WHERE prior.candidate_record_id = cr.id
                  AND prior.provider = %s AND prior.provider_version = %s
                  AND prior.query_address = COALESCE(
                    NULLIF(cr.parsed_fields->>'address', ''), cr.normalized_address, ''
                  )
                  AND prior.query_administrative_code IS NOT DISTINCT FROM cr.administrative_code
              )
            ORDER BY cr.processed_at, cr.id
            LIMIT %s
            """,
            (
                candidate_record_id,
                candidate_record_id,
                policy.provider,
                policy.version,
                limit,
            ),
        ).fetchall()
        return [
            GeocodeCandidate(
                candidate_record_id=str(row[0]),
                source_record_id=str(row[1]),
                address=str(row[2]) if row[2] is not None else None,
                normalized_address=str(row[3]) if row[3] is not None else None,
                administrative_code=str(row[4]) if row[4] is not None else None,
            )
            for row in rows
        ]

    def count_processed(self, policy: ProviderPolicy) -> int:
        row = self._connection.execute(
            """
            SELECT count(DISTINCT candidate_record_id)
            FROM app_private.candidate_locations
            WHERE provider = %s AND provider_version = %s
            """,
            (policy.provider, policy.version),
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def persistent_storage_allowed(self, policy: ProviderPolicy) -> bool:
        row = self._connection.execute(
            """
            SELECT persistent_storage_allowed
            FROM app_private.geocode_provider_policies
            WHERE provider = %s AND provider_version = %s
            """,
            (policy.provider, policy.version),
        ).fetchone()
        if row is None:
            raise RuntimeError("geocode provider has no approved database policy")
        return bool(row[0])

    def approved_policy(self, provider: str, version: str) -> ProviderPolicy:
        row = self._connection.execute(
            """
            SELECT persistent_storage_allowed, quota_per_run, requests_per_second
            FROM app_private.geocode_provider_policies
            WHERE provider = %s AND provider_version = %s
            """,
            (provider, version),
        ).fetchone()
        if row is None:
            raise RuntimeError("geocode provider has no approved database policy")
        return ProviderPolicy(provider, version, bool(row[0]), int(row[1]), float(row[2]))

    def region_parents(self, codes: set[str]) -> dict[str, str | None]:
        if not codes:
            return {}
        rows = self._connection.execute(
            """
            SELECT DISTINCT ON (child.adcode) child.adcode, parent.adcode
            FROM app_private.regions child
            LEFT JOIN app_private.regions parent ON parent.id = child.parent_id
            ORDER BY child.adcode, (child.valid_to IS NULL) DESC,
              child.valid_from DESC NULLS LAST, child.version DESC
            """
        ).fetchall()
        parents = {str(code): str(parent) if parent is not None else None for code, parent in rows}
        # Preserve unknown codes as absent so validation safely sends them to review.
        return parents

    def persist(
        self,
        policy: ProviderPolicy,
        candidate: GeocodeCandidate,
        result: GeocodeResult,
        validation: CoordinateValidation,
        address_fingerprint: str,
        result_fingerprint: str,
        request_at: datetime,
        retrieval_at: datetime,
    ) -> bool:
        verified_at = retrieval_at if validation.status.value == "verified" else None
        with self._connection.transaction():
            row = self._connection.execute(
                """
                INSERT INTO app_private.candidate_locations (
                  candidate_record_id, source_record_id, provider, provider_version,
                  provider_record_id, query_address, query_administrative_code,
                  address_fingerprint, result_fingerprint, returned_address, returned_adcode,
                  longitude_wgs84, latitude_wgs84, original_coordinate_system,
                  stored_coordinate_system, accuracy_m, precision_level, geocode_result_type,
                  validation_status, error_code, validation_reason, source_metadata,
                  request_at, retrieval_at, verified_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  'WGS84', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (
                  candidate_record_id, provider, provider_version,
                  address_fingerprint, result_fingerprint
                ) DO NOTHING
                RETURNING id
                """,
                (
                    candidate.candidate_record_id,
                    candidate.source_record_id,
                    policy.provider,
                    policy.version,
                    result.provider_record_id,
                    candidate.address or "",
                    candidate.administrative_code,
                    address_fingerprint,
                    result_fingerprint,
                    result.returned_address,
                    result.returned_adcode,
                    validation.longitude_wgs84,
                    validation.latitude_wgs84,
                    result.original_coordinate_system.value,
                    result.accuracy_m,
                    result.precision_level.value,
                    result.result_type,
                    validation.status.value,
                    validation.error_code.value if validation.error_code else None,
                    validation.reason,
                    Jsonb(result.source_metadata),
                    request_at,
                    retrieval_at,
                    verified_at,
                ),
            ).fetchone()
            return row is not None
