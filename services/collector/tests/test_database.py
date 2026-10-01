from __future__ import annotations

import csv
import hashlib
import io
import os
import zipfile
from datetime import date, datetime
from pathlib import Path

import psycopg
import pytest
from openpyxl import Workbook

from eye_collector.db import PostgresRepository
from eye_collector.exceptions import SourcePolicyError
from eye_collector.http import HttpClient
from eye_collector.models import FileImportProvenance, SourceDescriptor, SourcePage
from eye_collector.policy import SourcePolicy
from eye_collector.runner import CollectorRunner
from eye_collector.sources.fixture import FixtureSourceAdapter, FixtureTransport
from eye_collector.sources.open_data_file import (
    BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS,
    BEIJING_HOSPITALS,
    SHENZHEN_BAOAN_HOSPITALS,
    OpenDataFileAdapter,
)

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


def test_database_approved_manual_file_snapshot_is_idempotent(tmp_path: Path) -> None:
    source_file = tmp_path / "synthetic-beijing.csv"
    with source_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["机构名称"])
        writer.writerow(["数据库集成测试医院"])
    original_bytes = source_file.read_bytes()
    provenance = FileImportProvenance(
        original_filename=source_file.name,
        file_sha256=hashlib.sha256(original_bytes).hexdigest(),
        file_size_bytes=len(original_bytes),
        obtained_at=datetime.fromisoformat("2026-10-01T10:00:00+08:00"),
        operator="integration-test-operator",
        acquisition_method="official_portal_manual_download",
    )
    adapter = OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)
    repository = PostgresRepository.connect(database_url())
    try:
        first = CollectorRunner(repository, adapter, file_provenance=provenance).run(
            "110000", limit=1
        )
        second = CollectorRunner(repository, adapter, file_provenance=provenance).run(
            "110000", limit=1
        )
    finally:
        repository.close()

    assert (first.status, first.counts.inserted) == ("succeeded", 1)
    assert (second.status, second.counts.unchanged) == ("succeeded", 1)
    with psycopg.connect(database_url(), autocommit=True) as connection:
        row = connection.execute(
            """
            SELECT count(*), min(raw_payload->>'name'), min(source_url)
            FROM app_private.source_records AS records
            JOIN app_private.source_catalog AS sources ON sources.id = records.source_id
            WHERE sources.name = %s AND records.source_key = %s
            """,
            (BEIJING_HOSPITALS.source_name, "数据库集成测试医院"),
        ).fetchone()
    assert row == (1, "数据库集成测试医院", BEIJING_HOSPITALS.dataset_url)


def test_database_file_provenance_is_linked_and_replay_keeps_snapshots_idempotent(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "official-designated.csv"
    with source_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.expected_headers)
        writer.writerow(
            [
                1,
                "真实名称格式测试医院",
                "12345",
                "110101",
                "01",
                "03",
                "测试地址",
                "row-1",
                "created",
                "updated",
            ]
        )
    original_bytes = source_file.read_bytes()
    provenance = FileImportProvenance(
        original_filename=source_file.name,
        file_sha256=hashlib.sha256(original_bytes).hexdigest(),
        file_size_bytes=len(original_bytes),
        obtained_at=datetime.fromisoformat("2026-10-01T10:00:00+08:00"),
        operator="integration-test-operator",
        acquisition_method="official_portal_manual_download",
    )
    adapter = OpenDataFileAdapter(source_file, BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS)
    repository = PostgresRepository.connect(database_url())
    try:
        first = CollectorRunner(repository, adapter, file_provenance=provenance).run(
            "110000", limit=1
        )
        second = CollectorRunner(repository, adapter, file_provenance=provenance).run(
            "110000", limit=1
        )
    finally:
        repository.close()

    assert (first.status, first.counts.inserted) == ("succeeded", 1)
    assert (second.status, second.counts.unchanged) == ("succeeded", 1)
    assert source_file.read_bytes() == original_bytes
    with psycopg.connect(database_url(), autocommit=True) as connection:
        rows = connection.execute(
            """
            SELECT count(*), count(DISTINCT ir.id), min(ir.file_sha256),
                   min(ir.file_original_filename), min(ir.file_size_bytes),
                   min(ir.file_dataset_page), min(ir.file_source_updated_at),
                   min(ir.file_operator), min(ir.file_acquisition_method),
                   min(extract(epoch FROM ir.file_obtained_at))
            FROM app_private.import_runs AS ir
            JOIN app_private.source_catalog AS sources ON sources.id = ir.source_id
            WHERE sources.name = %s AND ir.file_sha256 = %s
            """,
            (BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_name, provenance.file_sha256),
        ).fetchone()
        snapshot_count = connection.execute(
            """
            SELECT count(*) FROM app_private.source_records AS records
            WHERE records.import_run_id IN (
              SELECT id FROM app_private.import_runs WHERE file_sha256 = %s
            )
            """,
            (provenance.file_sha256,),
        ).fetchone()
    assert rows == (
        2,
        2,
        provenance.file_sha256,
        source_file.name,
        len(original_bytes),
        BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.dataset_url,
        date(2026, 8, 13),
        "integration-test-operator",
        "official_portal_manual_download",
        pytest.approx(provenance.obtained_at.timestamp()),
    )
    assert snapshot_count == (1,)


def test_database_source_rights_match_real_export_business_mappings() -> None:
    expected = {
        BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_name: {
            "source_fields",
            "name",
            "address",
            "administrative_code",
            "hospital_grade",
            "source_category",
            "registration_id",
        },
        SHENZHEN_BAOAN_HOSPITALS.source_name: {
            "source_fields",
            "source_reference_id",
            "name",
            "administrative_context",
            "address",
            "source_category",
            "hospital_level",
            "hospital_grade",
            "specialties",
            "hospital_description",
        },
    }
    with psycopg.connect(database_url(), autocommit=True) as connection:
        for source_name, fields in expected.items():
            actual = connection.execute(
                "SELECT permitted_fields FROM app_private.source_catalog WHERE name = %s",
                (source_name,),
            ).fetchone()
            assert actual is not None and set(actual[0]) == fields


def test_database_zip_replay_preserves_member_provenance_and_changed_snapshots(
    tmp_path: Path,
) -> None:
    dataset = SHENZHEN_BAOAN_HOSPITALS
    workbook = Workbook()
    workbook.active.title = "资源描述信息"
    sheet = workbook.create_sheet("数据集1")
    sheet.append(list(dataset.expected_headers))
    base = {header: "" for header in dataset.expected_headers}
    base.update({"文档ID": "duplicate-doc", "名称": "同名测试医院", "所在区县": "宝安区"})
    first = dict(base)
    first["医院简介"] = "普通综合医院"
    changed = dict(base)
    changed["医院简介"] = "设有眼科门诊"
    identical = dict(first)
    for row in (first, changed, identical):
        sheet.append([row[header] for header in dataset.expected_headers])
    member_buffer = io.BytesIO()
    workbook.save(member_buffer)
    member_bytes = member_buffer.getvalue()
    member_name = "宝安区-医院基本信息_2920002800636.xlsx"
    archive_path = tmp_path / "宝安区-医院基本信息20261001071251275982.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member_name, member_bytes)
    archive_bytes = archive_path.read_bytes()
    provenance = FileImportProvenance(
        original_filename=archive_path.name,
        file_sha256=hashlib.sha256(archive_bytes).hexdigest(),
        file_size_bytes=len(archive_bytes),
        obtained_at=datetime.fromisoformat("2026-10-01T10:00:00+08:00"),
        operator="integration-test-operator",
        acquisition_method="official_portal_manual_download",
        member_name=member_name,
        member_sha256=hashlib.sha256(member_bytes).hexdigest(),
        member_size_bytes=len(member_bytes),
    )
    adapter = OpenDataFileAdapter(archive_path, dataset)
    repository = PostgresRepository.connect(database_url())
    try:
        first_run = CollectorRunner(repository, adapter, file_provenance=provenance).run(
            "440306", limit=3
        )
        replay = CollectorRunner(repository, adapter, file_provenance=provenance).run(
            "440306", limit=3
        )
    finally:
        repository.close()

    assert (first_run.status, first_run.counts.inserted, first_run.counts.unchanged) == (
        "succeeded",
        2,
        1,
    )
    assert (replay.status, replay.counts.inserted, replay.counts.unchanged) == (
        "succeeded",
        0,
        3,
    )
    assert archive_path.read_bytes() == archive_bytes
    with psycopg.connect(database_url(), autocommit=True) as connection:
        run_metadata = connection.execute(
            """
            SELECT file_original_filename, file_sha256, file_size_bytes,
                   file_member_name, file_member_sha256, file_member_size_bytes
            FROM app_private.import_runs
            WHERE file_sha256 = %s AND source_id = (
              SELECT id FROM app_private.source_catalog WHERE name = %s
            )
            ORDER BY started_at
            """,
            (provenance.file_sha256, dataset.source_name),
        ).fetchall()
        snapshots = connection.execute(
            """
            SELECT count(*), count(DISTINCT content_hash), count(DISTINCT source_key)
            FROM app_private.source_records
            WHERE source_id = (SELECT id FROM app_private.source_catalog WHERE name = %s)
              AND source_key = 'duplicate-doc'
            """,
            (dataset.source_name,),
        ).fetchone()
    assert len(run_metadata) == 2
    assert all(
        row
        == (
            archive_path.name,
            provenance.file_sha256,
            len(archive_bytes),
            member_name,
            provenance.member_sha256,
            len(member_bytes),
        )
        for row in run_metadata
    )
    assert snapshots == (2, 2, 1)


def test_database_inspect_source_is_read_only() -> None:
    descriptor = SourceDescriptor(
        BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_key,
        BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.source_name,
        BEIJING_DESIGNATED_MEDICAL_INSTITUTIONS.dataset_url,
        access_method="file",
    )
    repository = PostgresRepository.connect(database_url())
    try:
        with psycopg.connect(database_url(), autocommit=True) as connection:
            before = connection.execute("SELECT count(*) FROM app_private.import_runs").fetchone()
        registration = repository.inspect_source(descriptor)
        with psycopg.connect(database_url(), autocommit=True) as connection:
            after = connection.execute("SELECT count(*) FROM app_private.import_runs").fetchone()
    finally:
        repository.close()

    assert registration is not None
    assert registration.status == "approved"
    assert registration.access_policy == "manual_only"
    assert registration.pilot_group_record_limit == 300
    assert registration.dataset_page == descriptor.catalog_url
    assert registration.source_updated_at.isoformat() == "2026-08-13"
    assert before == after


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
    descriptor = SourceDescriptor("unknown", "Unknown Directory", "https://fixture.invalid/unknown")
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
