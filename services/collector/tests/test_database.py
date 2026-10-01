from __future__ import annotations

import os

import psycopg
import pytest

from eye_collector.db import PostgresRepository
from eye_collector.exceptions import SourcePolicyError
from eye_collector.http import HttpClient
from eye_collector.models import SourceDescriptor, SourcePage
from eye_collector.policy import SourcePolicy
from eye_collector.runner import CollectorRunner
from eye_collector.sources.fixture import FixtureSourceAdapter, FixtureTransport

pytestmark = pytest.mark.database


def database_url() -> str:
    value = os.getenv("DATABASE_URL", "")
    if not value:
        pytest.skip("DATABASE_URL is required for database-marked tests")
    return value


def make_runner(revision: str = "stable") -> tuple[PostgresRepository, HttpClient, CollectorRunner]:
    config_url = database_url()
    repository = PostgresRepository.connect(config_url)
    client = HttpClient(
        timeout_seconds=2,
        max_response_bytes=32_768,
        max_attempts=3,
        backoff_base_seconds=0,
        user_agent="collector-database-tests/1.0",
        transport=FixtureTransport(revision=revision),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )
    adapter = FixtureSourceAdapter(client, revision=revision)
    return repository, client, CollectorRunner(repository, adapter)


def test_database_fixture_snapshots_are_idempotent_and_changed_content_is_historical() -> None:
    with psycopg.connect(database_url(), autocommit=True) as connection:
        existing_runs = connection.execute(
            """
            SELECT count(*) FROM app_private.import_runs ir
            JOIN app_private.source_catalog sc ON sc.id = ir.source_id
            WHERE sc.name = 'Fixture Directory'
            """
        ).fetchone()
    assert existing_runs is not None

    repository, client, runner = make_runner()
    try:
        first = runner.run("110000")
        second = runner.run("110000")
    finally:
        client.close()
        repository.close()

    repository3, client3, runner3 = make_runner("updated")
    try:
        updated = runner3.run("110000")
    finally:
        client3.close()
        repository3.close()

    assert (first.status, first.counts.requested, first.counts.received) == ("succeeded", 2, 8)
    assert (first.counts.inserted, first.counts.unchanged) == (7, 1)
    assert (second.counts.inserted, second.counts.unchanged) == (0, 8)
    assert (updated.counts.inserted, updated.counts.unchanged) == (1, 7)

    with psycopg.connect(database_url(), autocommit=True) as connection:
        rows = connection.execute(
            """
            SELECT count(*), count(*) FILTER (WHERE raw_payload->>'updated_at' = '2026-09-15')
            FROM app_private.source_records sr
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            WHERE sc.name = 'Fixture Directory' AND sr.source_key = 'clinic-002'
            """
        ).fetchone()
        assert rows == (2, 1)

        valid_links = connection.execute(
            """
            SELECT count(*)
            FROM app_private.source_records sr
            JOIN app_private.import_runs ir ON ir.id = sr.import_run_id
            JOIN app_private.source_catalog sc ON sc.id = sr.source_id
            WHERE sc.name = 'Fixture Directory'
            """
        ).fetchone()
        assert valid_links is not None and valid_links[0] == 8

        run_states = connection.execute(
            """
            SELECT count(*), count(*) FILTER (
              WHERE ir.status = 'succeeded' AND ir.ended_at IS NOT NULL
            )
            FROM app_private.import_runs ir
            JOIN app_private.source_catalog sc ON sc.id = ir.source_id
            WHERE sc.name = 'Fixture Directory'
            """
        ).fetchone()
        assert run_states == (existing_runs[0] + 3, existing_runs[0] + 3)


def test_database_failed_run_is_closed_and_error_is_redacted() -> None:
    repository = PostgresRepository.connect(database_url())
    client = HttpClient(
        timeout_seconds=2,
        max_response_bytes=32_768,
        max_attempts=2,
        backoff_base_seconds=0,
        user_agent="collector-database-tests/1.0",
        transport=FixtureTransport(),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )

    class FailingAdapter(FixtureSourceAdapter):
        def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
            if cursor is not None:
                raise RuntimeError("Authorization: Bearer integration-secret")
            return super().fetch_page(region_code, cursor)

    try:
        result = CollectorRunner(repository, FailingAdapter(client)).run("110000")
    finally:
        client.close()
        repository.close()

    assert result.status == "failed"
    assert result.counts.received == 3
    assert result.counts.inserted + result.counts.unchanged == 3
    with psycopg.connect(database_url(), autocommit=True) as connection:
        row = connection.execute(
            """
            SELECT status, ended_at IS NOT NULL, error_summary
            FROM app_private.import_runs WHERE id = %s
            """,
            (result.run_id,),
        ).fetchone()
    assert row is not None
    assert row[0:2] == ("failed", True)
    assert "integration-secret" not in str(row[2])
    assert "<redacted>" in str(row[2])


def test_database_cancelled_run_has_terminal_timestamp() -> None:
    repository, client, _ = make_runner()

    class InterruptAdapter(FixtureSourceAdapter):
        def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
            raise KeyboardInterrupt

    adapter = InterruptAdapter(client)
    try:
        with pytest.raises(KeyboardInterrupt):
            CollectorRunner(repository, adapter).run("110000")
    finally:
        client.close()
        repository.close()

    with psycopg.connect(database_url(), autocommit=True) as connection:
        row = connection.execute(
            """
            SELECT ir.status, ir.ended_at IS NOT NULL
            FROM app_private.import_runs ir
            JOIN app_private.source_catalog sc ON sc.id = ir.source_id
            WHERE sc.name = 'Fixture Directory' AND ir.status = 'cancelled'
            ORDER BY ir.started_at DESC LIMIT 1
            """
        ).fetchone()
    assert row == ("cancelled", True)


@pytest.mark.parametrize(
    ("source_name", "source_url"),
    [
        ("Fixture Pending Directory", "https://fixture.invalid/pending"),
        ("Fixture Suspended Directory", "https://fixture.invalid/suspended"),
        ("Fixture Blocked Directory", "https://fixture.invalid/blocked"),
    ],
)
def test_database_policy_rejects_sources_before_run_insert(
    source_name: str, source_url: str
) -> None:
    repository = PostgresRepository.connect(database_url())
    descriptor = SourceDescriptor("fixture-test", source_name, source_url)
    try:
        with pytest.raises(SourcePolicyError):
            repository.start_approved_run(descriptor, "110000", SourcePolicy())
        with psycopg.connect(database_url(), autocommit=True) as connection:
            row = connection.execute(
                """
                SELECT count(*)
                FROM app_private.import_runs ir
                JOIN app_private.source_catalog sc ON sc.id = ir.source_id
                WHERE sc.name = %s AND sc.url = %s
                """,
                (source_name, source_url),
            ).fetchone()
            assert row == (0,)
    finally:
        repository.close()


def test_database_policy_rejects_unknown_source_before_run_insert() -> None:
    repository = PostgresRepository.connect(database_url())
    descriptor = SourceDescriptor(
        "unknown", "Unknown Directory", "https://fixture.invalid/unknown"
    )
    try:
        with psycopg.connect(database_url(), autocommit=True) as connection:
            before = connection.execute("SELECT count(*) FROM app_private.import_runs").fetchone()
        with pytest.raises(SourcePolicyError, match="not registered"):
            repository.start_approved_run(descriptor, "110000", SourcePolicy())
        with psycopg.connect(database_url(), autocommit=True) as connection:
            count = connection.execute("SELECT count(*) FROM app_private.import_runs").fetchone()
        assert count == before
    finally:
        repository.close()


def test_collector_login_is_not_superuser_and_cannot_write_facilities() -> None:
    with psycopg.connect(database_url(), autocommit=True) as connection:
        current_user = connection.execute("SELECT current_user").fetchone()
        assert current_user == ("eye_collector_runtime",)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("INSERT INTO app_private.facilities DEFAULT VALUES")
