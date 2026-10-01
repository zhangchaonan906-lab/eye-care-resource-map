from __future__ import annotations

from eye_collector.http import HttpClient
from eye_collector.sources.fixture import FixtureSourceAdapter, FixtureTransport


def make_adapter(revision: str = "stable", scenario: str = "normal") -> tuple[
    FixtureSourceAdapter, HttpClient
]:
    client = HttpClient(
        timeout_seconds=1,
        max_response_bytes=16_384,
        max_attempts=3,
        backoff_base_seconds=0,
        user_agent="fixture-tests/1.0",
        transport=FixtureTransport(revision=revision, scenario=scenario),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )
    return FixtureSourceAdapter(client, revision=revision), client


def test_fixture_adapter_reads_multiple_pages_and_keeps_duplicate_snapshot() -> None:
    adapter, client = make_adapter()
    with client:
        records = list(adapter.iter_records("110000"))

    assert len(records) == 8
    assert len({record.source_key for record in records}) == 7
    assert records[0].source_key == "clinic-001"
    assert records[2] == records[3]
    assert records[0].raw_payload["address"] == "北京市朝阳区样例路1号"
    assert records[0].source_url == "https://fixture.invalid/facilities/clinic-001"


def test_fixture_updated_revision_changes_one_raw_snapshot() -> None:
    adapter, client = make_adapter(revision="updated")
    with client:
        records = list(adapter.iter_records("110000"))

    updated = next(record for record in records if record.source_key == "clinic-002")
    assert updated.raw_payload["updated_at"] == "2026-09-15"
    assert updated.raw_payload["name"].endswith("（更新版）")


def test_fixture_transport_simulates_retriable_http_failures() -> None:
    for scenario in ("retry_429", "retry_500", "timeout"):
        adapter, client = make_adapter(scenario=scenario)
        with client:
            records = list(adapter.iter_records("110000", limit=1))
        assert len(records) == 1


def test_fixture_never_emits_unapproved_or_derived_fields() -> None:
    adapter, client = make_adapter()
    with client:
        record = next(adapter.iter_records("110000", limit=1))

    assert set(record.raw_payload) == {"name", "address", "region", "updated_at"}
