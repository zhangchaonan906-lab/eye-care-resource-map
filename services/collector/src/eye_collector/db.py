from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import RawRecord, SourceDescriptor, SourceRegistration
from eye_collector.policy import SourcePolicy


class PostgresRepository:
    """All PostgreSQL operations used by the collector, bound to one connection."""

    def __init__(self, connection: psycopg.Connection[tuple[Any, ...]]) -> None:
        self._connection = connection

    @classmethod
    def connect(cls, database_url: str) -> PostgresRepository:
        return cls(psycopg.connect(database_url, row_factory=tuple_row, autocommit=True))

    def close(self) -> None:
        self._connection.close()

    def start_approved_run(
        self,
        descriptor: SourceDescriptor,
        region_code: str,
        policy: SourcePolicy,
    ) -> tuple[str, SourceRegistration]:
        """Lock, approve, and insert a running import in one transaction."""
        with self._connection.transaction():
            self._connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            rows = self._connection.execute(
                """
                SELECT id::text, name, url, use_basis, permitted_fields,
                       access_policy, status
                FROM app_private.source_catalog
                WHERE name = %s AND url = %s
                LIMIT 2
                """,
                (descriptor.source_name, descriptor.catalog_url),
            ).fetchall()
            if len(rows) > 1:
                raise SourcePolicyError("source registration is ambiguous")
            registration = self._registration(rows[0]) if rows else None
            policy.authorize(registration, access_method=descriptor.access_method)
            assert registration is not None
            run_row = self._connection.execute(
                """
                INSERT INTO app_private.import_runs (source_id, region_code, status)
                SELECT id, %s, 'running'
                FROM app_private.source_catalog
                WHERE id = %s AND status = 'approved'
                RETURNING id::text
                """,
                (region_code, registration.id),
            ).fetchone()
            if run_row is None:
                raise SourcePolicyError("source approval changed before import run creation")
            return str(run_row[0]), registration

    @staticmethod
    def _registration(row: tuple[Any, ...]) -> SourceRegistration:
        return SourceRegistration(
            id=str(row[0]),
            name=str(row[1]),
            url=str(row[2]),
            use_basis=str(row[3]),
            permitted_fields=frozenset(row[4]),
            access_policy=row[5],
            status=str(row[6]),
        )

    def snapshot_exists(self, source_id: str, record: RawRecord, content_hash: str) -> bool:
        row = self._connection.execute(
            """
            SELECT 1 FROM app_private.source_records
            WHERE source_id = %s AND source_key = %s AND content_hash = %s
            """,
            (source_id, record.source_key, content_hash),
        ).fetchone()
        return row is not None

    def insert_snapshot(
        self,
        run_id: str,
        source_id: str,
        record: RawRecord,
        content_hash: str,
    ) -> bool:
        row = self._connection.execute(
            """
            INSERT INTO app_private.source_records
              (source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, source_key, content_hash) DO NOTHING
            RETURNING id
            """,
            (
                source_id,
                record.source_key,
                Jsonb(record.raw_payload),
                record.source_url,
                content_hash,
                run_id,
            ),
        ).fetchone()
        return row is not None

    def finish_run(
        self,
        run_id: str,
        status: str,
        counts: dict[str, int],
        error_summary: str | None = None,
    ) -> None:
        if status not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("run status must be terminal")
        if status == "failed" and not error_summary:
            raise ValueError("failed runs require an error summary")
        row = self._connection.execute(
            """
            UPDATE app_private.import_runs
            SET status = %s, ended_at = now(), counts = %s, error_summary = %s
            WHERE id = %s AND status = 'running'
            RETURNING id
            """,
            (status, Jsonb(counts), error_summary, run_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("import run was missing or already terminal")
