from __future__ import annotations

import os

import psycopg
import pytest

from eye_collector.etl.pipeline import Pipeline
from eye_collector.etl.repository import ETLRepository
from eye_collector.hashing import canonical_sha256

pytestmark = pytest.mark.etl_database


def _url(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        pytest.skip(f"{name} is required for P3 ETL database tests")
    return value


def test_etl_pipeline_persists_traceable_candidates_and_is_idempotent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    admin_url = _url("DATABASE_ADMIN_URL")
    etl_url = _url("ETL_DATABASE_URL")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(
            """
            INSERT INTO app_private.regions (adcode, name, level, version)
            VALUES ('110105', 'synthetic district', 'district', 'p3-test')
            ON CONFLICT (adcode, version) DO NOTHING
            """
        )
        region_id = admin.execute(
            "SELECT id FROM app_private.regions WHERE adcode = '110105' AND version = 'p3-test'"
        ).fetchone()[0]
        organization = admin.execute(
            "SELECT id FROM app_private.organizations WHERE registration_id = 'SYN-001'"
        ).fetchone()
        if organization is None:
            organization = admin.execute(
                """
                INSERT INTO app_private.organizations (canonical_name, registration_id)
                VALUES ('Synthetic organization', 'SYN-001') RETURNING id
                """
            ).fetchone()
        assert organization is not None
        org_id = organization[0]
        for name, campus in (
            ("Synthetic organization", "\u4e1c\u9662"),
            ("\u6837\u4f8b\u4e2d\u5fc3", "\u5317\u533a"),
        ):
            existing = admin.execute(
                """
                SELECT id FROM app_private.facilities
                WHERE name = %s AND campus_name IS NOT DISTINCT FROM %s AND region_id = %s
                """,
                (name, campus, region_id),
            ).fetchone()
            if existing is None:
                admin.execute(
                    """
                    INSERT INTO app_private.facilities (
                      organization_id, name, normalized_name, campus_name,
                      category, region_id, address
                    ) VALUES (%s, %s, %s, %s, 'unknown', %s, 'synthetic fixture address')
                    """,
                    (
                        org_id if name == "Synthetic organization" else None,
                        name,
                        name.casefold(),
                        campus,
                        region_id,
                    ),
                )

        raw_before = admin.execute(
            """
            SELECT sr.id, sr.raw_payload
            FROM app_private.source_records sr
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            WHERE sc.name = 'Fixture Directory'
            ORDER BY sr.id
            """
        ).fetchall()
        assert len(raw_before) == 8
        published_before = admin.execute(
            "SELECT count(*) FROM app_private.facilities WHERE verification_status = 'published'"
        ).fetchone()[0]

    repository = ETLRepository.connect(etl_url)
    try:
        stats = Pipeline(repository).run()
        repeat_stats = Pipeline(repository).run()
    finally:
        repository.close()

    assert stats.source_records_read == 8
    assert stats.errors == 0, [
        getattr(record, "error", None)
        for record in caplog.records
        if record.name == "eye_collector.etl"
    ]
    assert stats.candidates_created == 7
    assert stats.skipped == 1
    assert stats.errors == 0
    assert stats.evidence_created == 4
    assert stats.duplicate_cases == 2
    assert repeat_stats.source_records_read == 0
    assert repeat_stats.candidates_created == 0
    assert repeat_stats.already_processed == 7
    assert repeat_stats.skipped == 0
    assert repeat_stats.errors == 0

    with psycopg.connect(admin_url, autocommit=True) as admin:
        candidates = admin.execute(
            """
            SELECT cr.id, sr.raw_payload->>'name', cr.match_status,
              cr.proposed_facility_id, cr.normalized_name, sr.id,
              (SELECT count(*) FROM app_private.candidate_evidence ce
               WHERE ce.candidate_record_id = cr.id)
            FROM app_private.candidate_records cr
            JOIN app_private.source_records sr ON sr.id = cr.source_record_id
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            WHERE sc.name = 'Fixture Directory'
            """
        ).fetchall()
        assert len(candidates) == 7
        assert len({row[5] for row in candidates}) == 7
        assert all("\u773c\u79d1" not in row[1] or row[6] == 0 for row in candidates)
        assert sum(row[6] for row in candidates) == 4
        assert all(
            row[2] == "needs_review"
            for row in candidates
            if row[1] == "\u6837\u4f8b\u95e8\u8bca" or "\u4e1c\u9662" in row[1]
        )
        assert any(
            row[2] == "matched" and row[3] is not None and row[4] == "\u6837\u4f8b\u4e2d\u5fc3"
            for row in candidates
        )
        assert any(
            row[1] == "\u6837\u4f8b\u773c\u79d1\u533b\u9662" and row[2] == "unmatched"
            for row in candidates
        )
        assert not any(
            row[1] == "\u6837\u4f8b\u773c\u79d1\u533b\u9662" and row[6] > 0 for row in candidates
        )
        raw_after = admin.execute(
            """
            SELECT sr.id, sr.raw_payload
            FROM app_private.source_records sr
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            WHERE sc.name = 'Fixture Directory'
            ORDER BY sr.id
            """
        ).fetchall()
        assert raw_after == raw_before
        assert (
            admin.execute(
                "SELECT count(*) FROM app_private.facilities "
                "WHERE verification_status = 'published'"
            ).fetchone()[0]
            == published_before
        )
        duplicate_sizes = admin.execute(
            """
            SELECT count(*) FROM app_private.duplicate_case_candidates dcc
            JOIN app_private.duplicate_cases dc ON dc.id = dcc.duplicate_case_id
            WHERE dc.resolution = 'pending'
            GROUP BY dc.id
            """
        ).fetchall()
        assert sorted(row[0] for row in duplicate_sizes) == [2, 3]

    with psycopg.connect(etl_url, autocommit=True) as etl:
        assert etl.execute("SELECT current_user").fetchone() == ("eye_etl_runtime",)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            etl.execute("INSERT INTO app_private.facilities DEFAULT VALUES")
        with pytest.raises(psycopg.errors.CheckViolation, match="at least two candidates"):
            etl.execute(
                """
                INSERT INTO app_private.duplicate_cases (reason, match_fingerprint)
                VALUES ('synthetic singleton rejection', 'synthetic-singleton-rejection')
                """
            )


def test_p5_placeholder_evidence_and_duplicate_snapshots_stay_in_review_staging(caplog) -> None:
    admin_url = _url("DATABASE_ADMIN_URL")
    etl_url = _url("ETL_DATABASE_URL")
    payloads = (
        ("placeholder-row", {"name": "-", "source_fields": {"名称": "-"}}),
        (
            "baoan-copy-a",
            {
                "name": "Synthetic Baoan Hospital",
                "administrative_context": "宝安区",
                "address": "Synthetic Road 1",
                "source_fields": {"名称": "Synthetic Baoan Hospital"},
                "hospital_description": "医院配有眼底成像设备。",
            },
        ),
        (
            "baoan-copy-b",
            {
                "name": "Synthetic Baoan Hospital",
                "administrative_context": "宝安区",
                "address": "Synthetic Road 1",
                "source_fields": {"名称": "Synthetic Baoan Hospital"},
                "hospital_description": "设有眼科门诊。",
            },
        ),
    )
    with psycopg.connect(admin_url, autocommit=True) as admin:
        source_id, source_url = admin.execute(
            "SELECT id, url FROM app_private.source_catalog WHERE name = 'Fixture Directory'"
        ).fetchone()
        source_record_ids: dict[str, str] = {}
        for source_key, payload in payloads:
            run_id = admin.execute(
                """
                INSERT INTO app_private.import_runs (source_id, region_code, status)
                VALUES (%s, '440306', 'running') RETURNING id
                """,
                (source_id,),
            ).fetchone()[0]
            source_record_ids[source_key] = str(
                admin.execute(
                    """
                    INSERT INTO app_private.source_records (
                      source_id, source_key, raw_payload, source_url, content_hash, import_run_id
                    ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id::text
                    """,
                    (
                        source_id,
                        source_key,
                        psycopg.types.json.Jsonb(payload),
                        source_url,
                        canonical_sha256(payload),
                        run_id,
                    ),
                ).fetchone()[0]
            )
        raw_before = admin.execute(
            "SELECT id::text, raw_payload FROM app_private.source_records "
            "WHERE id = ANY(%s::uuid[])",
            ([value for value in source_record_ids.values()],),
        ).fetchall()

    repository = ETLRepository.connect(etl_url)
    try:
        stats = Pipeline(repository).run()
    finally:
        repository.close()

    assert stats.errors == 0, [
        (record.__dict__.get("error_type"), record.__dict__.get("error"))
        for record in caplog.records
        if record.__dict__.get("event") == "etl_record_failed"
    ]

    with psycopg.connect(admin_url, autocommit=True) as admin:
        raw_after = admin.execute(
            "SELECT id::text, raw_payload FROM app_private.source_records "
            "WHERE id = ANY(%s::uuid[])",
            ([value for value in source_record_ids.values()],),
        ).fetchall()
        placeholder = admin.execute(
            """
            SELECT disposition, reason_code FROM app_private.etl_source_dispositions
            WHERE source_record_id = %s AND pipeline_version = 'p3.3'
            """,
            (source_record_ids["placeholder-row"],),
        ).fetchone()
        placeholder_candidates = admin.execute(
            "SELECT count(*) FROM app_private.candidate_records WHERE source_record_id = %s",
            (source_record_ids["placeholder-row"],),
        ).fetchone()[0]
        evidence = admin.execute(
            """
            SELECT field_name, evidence_text FROM app_private.candidate_evidence
            WHERE source_record_id = %s
            """,
            (source_record_ids["baoan-copy-b"],),
        ).fetchone()
        duplicate_count = admin.execute(
            """
            SELECT count(*) FROM app_private.duplicate_case_candidates dcc
            JOIN app_private.candidate_records cr ON cr.id = dcc.candidate_record_id
            WHERE cr.source_record_id = ANY(%s::uuid[])
            """,
            ([source_record_ids["baoan-copy-a"], source_record_ids["baoan-copy-b"]],),
        ).fetchone()[0]

    assert sorted(raw_before) == sorted(raw_after)
    assert placeholder == ("terminal_skip", "invalid_name_placeholder")
    assert placeholder_candidates == 0
    assert evidence == ("hospital_description", "设有眼科门诊。")
    assert duplicate_count == 2


def test_manual_only_import_run_is_processed_only_when_explicitly_scoped() -> None:
    admin_url = _url("DATABASE_ADMIN_URL")
    etl_url = _url("ETL_DATABASE_URL")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        source = admin.execute(
            """
            SELECT id, url, access_policy, status
            FROM app_private.source_catalog WHERE name = 'P5 ETL Scope Synthetic'
            """
        ).fetchone()
        if source is None:
            source = admin.execute(
                """
                INSERT INTO app_private.source_catalog (
                  name, url, use_basis, permitted_fields, access_policy, status,
                  reviewed_at, registration_id_reliable
                ) VALUES (
                  'P5 ETL Scope Synthetic', 'https://fixture.invalid/p5-etl-scope',
                  'Synthetic integration test only', ARRAY['name', 'address'],
                  'manual_only', 'approved', now(), false
                ) RETURNING id, url, access_policy, status
                """
            ).fetchone()
        source_id, source_url, access_policy, status = source
        assert (access_policy, status) == ("manual_only", "approved")
        run_id = admin.execute(
            """
            INSERT INTO app_private.import_runs (source_id, region_code, status, ended_at)
            VALUES (%s, '110000', 'succeeded', now()) RETURNING id::text
            """,
            (source_id,),
        ).fetchone()[0]
        payload = {
            "name": "P5 scoped ETL synthetic hospital",
            "address": "Synthetic Road 1",
            "administrative_code": "110105",
            "registration_id": "P5-ETL-SCOPE-001",
        }
        source_record_id = admin.execute(
            """
            INSERT INTO app_private.source_records (
              source_id, source_key, raw_payload, source_url, content_hash, import_run_id
            ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id::text
            """,
            (
                source_id,
                "p5-etl-scope-synthetic-001",
                psycopg.types.json.Jsonb(payload),
                source_url,
                canonical_sha256(payload),
                run_id,
            ),
        ).fetchone()[0]

    repository = ETLRepository.connect(etl_url)
    try:
        Pipeline(repository).run()
        with psycopg.connect(admin_url, autocommit=True) as admin:
            assert admin.execute(
                "SELECT count(*) FROM app_private.candidate_records WHERE source_record_id = %s",
                (source_record_id,),
            ).fetchone()[0] == 0

        scoped_stats = Pipeline(repository).run(import_run_id=run_id)
        replay_stats = Pipeline(repository).run(import_run_id=run_id)
    finally:
        repository.close()

    assert scoped_stats.source_records_read == 1
    assert scoped_stats.candidates_created == 1
    assert scoped_stats.errors == 0
    assert replay_stats.source_records_read == 0
    assert replay_stats.candidates_created == 0
    assert replay_stats.already_processed == 1
    with psycopg.connect(etl_url, autocommit=True) as etl:
        assert etl.execute("SELECT current_user").fetchone() == ("eye_etl_runtime",)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            etl.execute("SELECT file_sha256 FROM app_private.import_runs LIMIT 1")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        candidate = admin.execute(
            """
            SELECT cr.source_record_id::text, cr.match_status, sr.raw_payload
            FROM app_private.candidate_records cr
            JOIN app_private.source_records sr ON sr.id = cr.source_record_id
            WHERE cr.source_record_id = %s
            """,
            (source_record_id,),
        ).fetchone()
    assert candidate == (source_record_id, "unmatched", payload)
