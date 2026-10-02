from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from eye_collector.changes import ChangeType, changed_json_paths
from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import (
    FileImportProvenance,
    RawRecord,
    SnapshotWriteResult,
    SourceDescriptor,
    SourceRegistration,
)
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
        if descriptor.access_method == "file":
            raise SourcePolicyError("manual file imports require file provenance")
        return self._start_approved_run(descriptor, region_code, policy)

    def start_approved_file_run(
        self,
        descriptor: SourceDescriptor,
        region_code: str,
        policy: SourcePolicy,
        provenance: FileImportProvenance,
    ) -> tuple[str, SourceRegistration]:
        if descriptor.access_method != "file":
            raise SourcePolicyError("file provenance is only valid for manual file imports")
        return self._start_approved_run(descriptor, region_code, policy, provenance)

    def _start_approved_run(
        self,
        descriptor: SourceDescriptor,
        region_code: str,
        policy: SourcePolicy,
        provenance: FileImportProvenance | None = None,
    ) -> tuple[str, SourceRegistration]:
        """Authorize a source and atomically insert an import run with optional provenance."""
        with self._connection.transaction():
            self._connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            rows = self._connection.execute(
                """
                SELECT source.id::text, source.name, source.url, source.use_basis,
                       source.permitted_fields, source.access_policy, source.status,
                       source.dataset_page, source.source_updated_at,
                       source.pilot_group_record_limit,
                       COALESCE((
                         SELECT count(*)
                         FROM app_private.source_records AS records
                         JOIN app_private.source_catalog AS grouped_source
                           ON grouped_source.id = records.source_id
                         WHERE grouped_source.pilot_group = source.pilot_group
                       ), 0)::integer
                FROM app_private.source_catalog AS source
                WHERE source.name = %s AND source.url = %s
                LIMIT 2
                """,
                (descriptor.source_name, descriptor.catalog_url),
            ).fetchall()
            if len(rows) > 1:
                raise SourcePolicyError("source registration is ambiguous")
            registration = self._registration(rows[0]) if rows else None
            policy.authorize(registration, access_method=descriptor.access_method)
            assert registration is not None
            if provenance is None:
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
            else:
                if registration.dataset_page is None:
                    raise SourcePolicyError("approved file source is missing its dataset page")
                run_row = self._connection.execute(
                    """
                    INSERT INTO app_private.import_runs (
                      source_id, region_code, status, file_original_filename,
                      file_sha256, file_size_bytes, file_obtained_at, file_dataset_page,
                      file_source_updated_at, file_operator, file_acquisition_method,
                      file_member_name, file_member_sha256, file_member_size_bytes
                    )
                    SELECT id, %s, 'running', %s, %s, %s, %s, dataset_page,
                           source_updated_at, %s, %s, %s, %s, %s
                    FROM app_private.source_catalog
                    WHERE id = %s AND status = 'approved'
                    RETURNING id::text
                    """,
                    (
                        region_code,
                        provenance.original_filename,
                        provenance.file_sha256,
                        provenance.file_size_bytes,
                        provenance.obtained_at,
                        provenance.operator,
                        provenance.acquisition_method,
                        provenance.member_name,
                        provenance.member_sha256,
                        provenance.member_size_bytes,
                        registration.id,
                    ),
                ).fetchone()
            if run_row is None:
                raise SourcePolicyError("source approval changed before import run creation")
            return str(run_row[0]), registration

    def inspect_source(self, descriptor: SourceDescriptor) -> SourceRegistration | None:
        """Read current source approval and pilot capacity in a read-only transaction."""
        with self._connection.transaction():
            self._connection.execute("SET TRANSACTION READ ONLY")
            rows = self._connection.execute(
                """
                SELECT source.id::text, source.name, source.url, source.use_basis,
                       source.permitted_fields, source.access_policy, source.status,
                       source.dataset_page, source.source_updated_at,
                       source.pilot_group_record_limit,
                       COALESCE((
                         SELECT count(*)
                         FROM app_private.source_records AS records
                         JOIN app_private.source_catalog AS grouped_source
                           ON grouped_source.id = records.source_id
                         WHERE grouped_source.pilot_group = source.pilot_group
                       ), 0)::integer
                FROM app_private.source_catalog AS source
                WHERE source.name = %s AND source.url = %s
                LIMIT 2
                """,
                (descriptor.source_name, descriptor.catalog_url),
            ).fetchall()
            if len(rows) > 1:
                raise SourcePolicyError("source registration is ambiguous")
            return self._registration(rows[0]) if rows else None

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
            dataset_page=row[7],
            source_updated_at=row[8],
            pilot_group_record_limit=row[9],
            pilot_group_record_count=int(row[10]),
        )

    def preview_snapshot(
        self, source_id: str, record: RawRecord, content_hash: str
    ) -> SnapshotWriteResult:
        exact = self._connection.execute(
            """SELECT id::text FROM app_private.source_records
               WHERE source_id=%s AND source_key=%s AND content_hash=%s""",
            (source_id, record.source_key, content_hash),
        ).fetchone()
        if exact is not None:
            return SnapshotWriteResult(ChangeType.UNCHANGED, source_record_id=str(exact[0]))
        previous = self._connection.execute(
            """SELECT id::text, raw_payload FROM app_private.source_records
               WHERE source_id=%s AND source_key=%s
               ORDER BY collected_at DESC, id DESC LIMIT 1""",
            (source_id, record.source_key),
        ).fetchone()
        if previous is None:
            return SnapshotWriteResult(ChangeType.NEW)
        paths, truncated = changed_json_paths(previous[1], record.raw_payload)
        return SnapshotWriteResult(
            ChangeType.CHANGED,
            previous_source_record_id=str(previous[0]),
            changed_paths=paths,
            diff_truncated=truncated,
        )

    def insert_snapshot(
        self,
        run_id: str,
        source_id: str,
        record: RawRecord,
        content_hash: str,
    ) -> SnapshotWriteResult:
        with self._connection.transaction():
            # Serialize classifications even when this is the first row for a key.
            self._connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"{source_id}:{record.source_key}",),
            )
            preview = self.preview_snapshot(source_id, record, content_hash)
            if preview.change_type is ChangeType.UNCHANGED:
                return preview
            row = self._connection.execute(
                """
                INSERT INTO app_private.source_records
                  (source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id, source_key, content_hash) DO NOTHING
                RETURNING id::text
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
            if row is None:
                exact = self._connection.execute(
                    """SELECT id::text FROM app_private.source_records
                       WHERE source_id=%s AND source_key=%s AND content_hash=%s""",
                    (source_id, record.source_key, content_hash),
                ).fetchone()
                if exact is None:
                    raise RuntimeError("snapshot conflict did not resolve to an existing row")
                return SnapshotWriteResult(ChangeType.UNCHANGED, source_record_id=str(exact[0]))

            source_record_id = str(row[0])
            self._connection.execute(
                """INSERT INTO app_private.source_change_events (
                     source_id, source_key, change_type, previous_source_record_id,
                     source_record_id, import_run_id, changed_paths, diff_truncated
                   ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    source_id,
                    record.source_key,
                    preview.change_type.value,
                    preview.previous_source_record_id,
                    source_record_id,
                    run_id,
                    list(preview.changed_paths),
                    preview.diff_truncated,
                ),
            )
            return SnapshotWriteResult(
                preview.change_type,
                source_record_id,
                preview.previous_source_record_id,
                preview.changed_paths,
                preview.diff_truncated,
            )

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
