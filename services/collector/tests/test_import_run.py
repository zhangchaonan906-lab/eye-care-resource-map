from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from eye_collector.exceptions import SourcePolicyError
from eye_collector.hashing import canonical_sha256
from eye_collector.models import (
    ImportCounts,
    RawRecord,
    SourceDescriptor,
    SourcePage,
    SourceRegistration,
)
from eye_collector.policy import SourcePolicy
from eye_collector.runner import CollectorRunner
from eye_collector.sources.base import SourceAdapter
from eye_collector.sources.open_data_file import BEIJING_HOSPITALS, OpenDataFileAdapter


@pytest.fixture
def registration() -> SourceRegistration:
    return SourceRegistration(
        "source-id",
        "Fixture Directory",
        "https://fixture.invalid/directory",
        "Synthetic local fixture",
        frozenset({"name", "address", "region", "updated_at"}),
        "automated_access_allowed",
        "approved",
    )


def make_record(key: str, name: str) -> RawRecord:
    return RawRecord(
        key,
        f"https://fixture.invalid/facilities/{key}",
        {
            "name": name,
            "address": "Fixture address",
            "region": "110000",
            "updated_at": "2026-09-01",
        },
    )


class MemoryRepository:
    def __init__(self, registration: SourceRegistration, *, terminal_error: bool = False) -> None:
        self.registration = registration
        self.terminal_error = terminal_error
        self.started = 0
        self.finished: list[tuple[str, ImportCounts, str | None]] = []
        self.snapshots: set[tuple[str, str, str]] = set()
        self.writes = 0

    def start_approved_run(
        self, descriptor: SourceDescriptor, region_code: str, policy: SourcePolicy
    ) -> tuple[str, SourceRegistration]:
        policy.authorize(self.registration, access_method=descriptor.access_method)
        self.started += 1
        return "run-id", self.registration

    def snapshot_exists(self, source_id: str, record: RawRecord, content_hash: str) -> bool:
        return (source_id, record.source_key, content_hash) in self.snapshots

    def insert_snapshot(
        self, run_id: str, source_id: str, record: RawRecord, content_hash: str
    ) -> bool:
        item = (source_id, record.source_key, content_hash)
        if item in self.snapshots:
            return False
        self.snapshots.add(item)
        self.writes += 1
        return True

    def finish_run(
        self, run_id: str, status: str, counts: dict[str, int], error_summary: str | None = None
    ) -> None:
        self.finished.append((status, ImportCounts(**counts), error_summary))
        if self.terminal_error:
            raise RuntimeError("terminal state update failed")


class MemoryAdapter(SourceAdapter):
    def __init__(self, pages: list[SourcePage], *, fail_after_first: bool = False) -> None:
        self.pages = pages
        self.fail_after_first = fail_after_first
        self.fetch_count = 0

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor("fixture", "Fixture Directory", "https://fixture.invalid/directory")

    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        self.fetch_count += 1
        if self.fail_after_first and self.fetch_count > 1:
            raise RuntimeError("fixture source failed")
        page_index = 0 if cursor is None else 1
        return self.pages[page_index]


def test_import_run_records_pages_records_and_idempotent_snapshots(
    registration: SourceRegistration,
) -> None:
    first = make_record("clinic-1", "Clinic One")
    second = make_record("clinic-2", "Clinic Two")
    third = make_record("clinic-3", "Clinic Three")
    adapter = MemoryAdapter(
        [SourcePage((first, second), "page-2"), SourcePage((first, third), None)]
    )
    repository = MemoryRepository(registration)

    result = CollectorRunner(repository, adapter).run("110000")  # type: ignore[arg-type]

    assert result.status == "succeeded"
    assert result.counts == ImportCounts(requested=2, received=4, inserted=3, unchanged=1)
    assert repository.finished[0][0] == "succeeded"


def test_changed_content_creates_a_new_snapshot(
    registration: SourceRegistration,
) -> None:
    repository = MemoryRepository(registration)
    first = MemoryAdapter([SourcePage((make_record("clinic-1", "Old name"),), None)])
    second = MemoryAdapter([SourcePage((make_record("clinic-1", "New name"),), None)])

    result1 = CollectorRunner(repository, first).run("110000")  # type: ignore[arg-type]
    result2 = CollectorRunner(repository, second).run("110000")  # type: ignore[arg-type]

    assert result1.counts.inserted == 1
    assert result2.counts.inserted == 1
    assert repository.writes == 2


def test_dry_run_counts_prospective_insert_without_writing(
    registration: SourceRegistration,
) -> None:
    repository = MemoryRepository(registration)
    adapter = MemoryAdapter([SourcePage((make_record("clinic-1", "Clinic One"),), None)])

    result = CollectorRunner(repository, adapter).run("110000", dry_run=True)

    assert result.dry_run is True
    assert result.counts.inserted == 1
    assert repository.writes == 0
    assert repository.finished[0][0] == "succeeded"


def test_adapter_failure_closes_run_as_failed(
    registration: SourceRegistration,
) -> None:
    repository = MemoryRepository(registration)
    adapter = MemoryAdapter(
        [SourcePage((make_record("clinic-1", "Clinic One"),), "page-2"), SourcePage((), None)],
        fail_after_first=True,
    )

    result = CollectorRunner(repository, adapter).run("110000")

    assert result.status == "failed"
    assert result.counts.failed == 1
    assert repository.finished[0][0] == "failed"
    assert repository.finished[0][2] == "RuntimeError: fixture source failed"


def test_interrupt_closes_run_as_cancelled_and_is_propagated(
    registration: SourceRegistration,
) -> None:
    repository = MemoryRepository(registration)

    class InterruptAdapter(MemoryAdapter):
        def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        CollectorRunner(repository, InterruptAdapter([])).run("110000")  # type: ignore[arg-type]

    assert repository.finished[0][0] == "cancelled"


def test_pending_source_is_rejected_before_start_or_fetch(
    registration: SourceRegistration,
) -> None:
    repository = MemoryRepository(replace(registration, status="pending"))
    adapter = MemoryAdapter([SourcePage((), None)])

    with pytest.raises(SourcePolicyError):
        CollectorRunner(repository, adapter).run("110000")  # type: ignore[arg-type]

    assert repository.started == 0
    assert adapter.fetch_count == 0


def test_dry_run_recognizes_existing_snapshot_as_unchanged(
    registration: SourceRegistration,
) -> None:
    record = make_record("clinic-1", "Clinic One")
    repository = MemoryRepository(registration)
    repository.snapshots.add(
        ("source-id", record.source_key, canonical_sha256(record.raw_payload))
    )
    adapter = MemoryAdapter([SourcePage((record,), None)])

    result = CollectorRunner(repository, adapter).run("110000", dry_run=True)

    assert result.counts.inserted == 0
    assert result.counts.unchanged == 1


def test_approved_manual_file_uses_existing_import_hash_and_idempotency(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "hospitals.csv"
    with source_file.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["机构名称"])
        writer.writerow(["北京测试医院"])
    adapter = OpenDataFileAdapter(source_file, BEIJING_HOSPITALS)
    registration = SourceRegistration(
        "source-id",
        BEIJING_HOSPITALS.source_name,
        BEIJING_HOSPITALS.dataset_url,
        "Official unconditional open dataset; imported from operator-downloaded file",
        frozenset({"source_fields", "name"}),
        "manual_only",
        "approved",
    )
    repository = MemoryRepository(registration)

    first = CollectorRunner(repository, adapter).run("110000", limit=1)  # type: ignore[arg-type]
    second = CollectorRunner(repository, adapter).run("110000", limit=1)  # type: ignore[arg-type]

    assert first.status == "succeeded"
    assert first.counts.inserted == 1
    assert second.status == "succeeded"
    assert second.counts.unchanged == 1
    assert repository.writes == 1
