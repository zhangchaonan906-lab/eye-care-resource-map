from __future__ import annotations

import os

import psycopg
import pytest

from eye_collector.geocoding.pipeline import GeocodingPipeline
from eye_collector.geocoding.providers.fixture import FixtureGeocoder, FixtureGeocodeTransport
from eye_collector.geocoding.repository import GeocodeRepository
from eye_collector.http import HttpClient

pytestmark = pytest.mark.geocode_database


def _url(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        pytest.skip(f"{name} is required for P4 geocoding database tests")
    return value


def _provider() -> FixtureGeocoder:
    return FixtureGeocoder(
        HttpClient(
            timeout_seconds=1,
            max_response_bytes=16_384,
            max_attempts=2,
            backoff_base_seconds=0,
            user_agent="synthetic-p4-geocoding-test/1.0",
            transport=FixtureGeocodeTransport(),
            sleeper=lambda _seconds: None,
            clock=lambda: 0,
            random_uniform=lambda _low, _high: 0,
        )
    )


def test_geocode_staging_is_idempotent_traceable_and_least_privilege() -> None:
    admin_url = _url("DATABASE_ADMIN_URL")
    geocode_url = _url("GEOCODE_DATABASE_URL")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        published_before = admin.execute(
            "SELECT count(*) FROM app_private.facilities "
            "WHERE verification_status = 'published'"
        ).fetchone()[0]
        facility_count_before = admin.execute(
            "SELECT count(*) FROM app_private.facilities"
        ).fetchone()[0]
        location_count_before = admin.execute(
            "SELECT count(*) FROM app_private.candidate_locations"
        ).fetchone()[0]

    repository = GeocodeRepository.connect(geocode_url)
    provider = _provider()
    try:
        dry_run_stats = GeocodingPipeline(repository, provider).run(dry_run=True)
        stats = GeocodingPipeline(repository, provider).run()
        with psycopg.connect(admin_url, autocommit=True) as admin:
            changed_candidate_id = admin.execute(
                "SELECT candidate_record_id::text FROM app_private.candidate_locations "
                "WHERE provider = 'fixture' ORDER BY candidate_record_id LIMIT 1"
            ).fetchone()[0]
            admin.execute(
                """
                UPDATE app_private.candidate_records
                SET parsed_fields = jsonb_set(parsed_fields, '{address}', '"P4 changed address"'),
                    normalized_address = 'p4 changed address'
                WHERE id = %s
                """,
                (changed_candidate_id,),
            )
        changed_stats = GeocodingPipeline(repository, provider).run(
            candidate_record_id=str(changed_candidate_id)
        )
        repeat_stats = GeocodingPipeline(repository, provider).run()
    finally:
        provider.close()
        repository.close()

    assert stats.candidates_read >= 2
    assert stats.geocode_requested <= 1_000
    assert stats.errors == 0
    assert stats.coordinates_created + stats.needs_review + stats.rejected >= 1
    assert dry_run_stats.coordinates_created == 0
    assert changed_stats.candidates_read == 1
    assert changed_stats.coordinates_created == 1
    assert repeat_stats.candidates_read == 0
    assert repeat_stats.already_processed >= 1
    assert repeat_stats.errors == 0

    with psycopg.connect(admin_url, autocommit=True) as admin:
        rows = admin.execute(
            """
            SELECT cl.validation_status, cl.longitude_wgs84, cl.latitude_wgs84,
              cl.stored_coordinate_system, cr.source_record_id = cl.source_record_id,
              cl.address_fingerprint, cl.result_fingerprint
            FROM app_private.candidate_locations cl
            JOIN app_private.candidate_records cr ON cr.id = cl.candidate_record_id
            WHERE cl.provider = 'fixture' AND cl.provider_version = 'fixture-v1'
            """
        ).fetchall()
        assert len(rows) >= 1
        assert all(row[4] for row in rows)
        assert all(row[3] == "WGS84" for row in rows)
        assert all(len(row[5]) == 64 and len(row[6]) == 64 for row in rows)
        assert admin.execute(
            "SELECT count(*) FROM app_private.candidate_locations"
        ).fetchone()[0] == location_count_before + stats.coordinates_created + 1
        changed_fingerprints = admin.execute(
            """
            SELECT address_fingerprint FROM app_private.candidate_locations
            WHERE candidate_record_id = %s ORDER BY created_at
            """,
            (changed_candidate_id,),
        ).fetchall()
        assert len(changed_fingerprints) == 2
        assert changed_fingerprints[0][0] != changed_fingerprints[1][0]
        assert (
            admin.execute("SELECT count(*) FROM app_private.facilities").fetchone()[0]
            == facility_count_before
        )
        assert (
            admin.execute(
                "SELECT count(*) FROM app_private.facilities "
                "WHERE verification_status = 'published'"
            ).fetchone()[0]
            == published_before
        )

    with psycopg.connect(geocode_url, autocommit=True) as geocode:
        assert geocode.execute("SELECT current_user").fetchone() == ("eye_geocode_runtime",)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            geocode.execute("INSERT INTO app_private.facilities DEFAULT VALUES")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            geocode.execute("UPDATE app_private.source_records SET raw_payload = '{}'::jsonb")

        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                """
                INSERT INTO app_private.geocode_provider_policies (
                  provider, provider_version, persistent_storage_allowed, quota_per_run,
                  requests_per_second, use_basis, reviewed_at
                ) VALUES ('synthetic-blocked', 'test-v1', false, 10, 1.0,
                          'test-only policy gate', now())
                """
            )
            candidate_id, source_record_id, query_address = admin.execute(
                """
                SELECT cr.id, cr.source_record_id,
                  COALESCE(NULLIF(cr.parsed_fields->>'address', ''), cr.normalized_address, '')
                FROM app_private.candidate_records cr ORDER BY cr.id LIMIT 1
                """
            ).fetchone()

        with pytest.raises(psycopg.errors.CheckViolation, match="blocks persistence"):
            geocode.execute(
                """
                INSERT INTO app_private.candidate_locations (
                  candidate_record_id, source_record_id, provider, provider_version,
                  query_address, address_fingerprint, result_fingerprint,
                  returned_address, longitude_wgs84, latitude_wgs84,
                  original_coordinate_system, accuracy_m, precision_level,
                  geocode_result_type, validation_status, error_code, request_at
                ) VALUES (%s, %s, 'synthetic-blocked', 'test-v1', %s, %s, %s,
                          'provider response', 116.397, 39.908, 'WGS84', 20,
                          'rooftop', 'rooftop', 'needs_review', 'POLICY_BLOCKED', now())
                """,
                (candidate_id, source_record_id, query_address, "a" * 64, "b" * 64),
            )

        geocode.execute(
            """
            INSERT INTO app_private.candidate_locations (
              candidate_record_id, source_record_id, provider, provider_version,
              query_address, address_fingerprint, result_fingerprint,
              original_coordinate_system, stored_coordinate_system, precision_level,
              geocode_result_type, validation_status, error_code, validation_reason,
              source_metadata, request_at
            ) VALUES (%s, %s, 'synthetic-blocked', 'test-v1', %s, %s, %s,
                      'UNKNOWN', 'WGS84', 'unknown', 'policy_blocked', 'needs_review',
                      'POLICY_BLOCKED', 'provider_response_persistence_not_allowed', '{}', now())
            """,
            (candidate_id, source_record_id, query_address, "c" * 64, "d" * 64),
        )
