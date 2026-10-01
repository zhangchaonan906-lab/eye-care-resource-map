from __future__ import annotations

from dataclasses import dataclass

import pytest

from eye_collector.exceptions import AdapterError
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage
from eye_collector.sources.base import SourceAdapter


@dataclass
class PagedAdapter(SourceAdapter):
    pages: dict[str | None, SourcePage]
    requested_cursors: list[str | None]

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor("test", "Test source", "https://test.invalid/list")

    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        assert region_code == "110000"
        self.requested_cursors.append(cursor)
        return self.pages[cursor]


def record(key: str) -> RawRecord:
    return RawRecord(key, f"https://test.invalid/{key}", {"name": key})


def test_adapter_iterates_pages_and_preserves_raw_records() -> None:
    adapter = PagedAdapter(
        pages={
            None: SourcePage((record("a"),), "page-2"),
            "page-2": SourcePage((record("b"),), None),
        },
        requested_cursors=[],
    )

    assert list(adapter.iter_records("110000")) == [record("a"), record("b")]
    assert adapter.requested_cursors == [None, "page-2"]


def test_adapter_stops_at_record_limit() -> None:
    adapter = PagedAdapter(
        pages={None: SourcePage((record("a"), record("b")), "page-2")},
        requested_cursors=[],
    )

    assert list(adapter.iter_records("110000", limit=1)) == [record("a")]
    assert adapter.requested_cursors == [None]


def test_adapter_rejects_repeated_page_cursor() -> None:
    adapter = PagedAdapter(
        pages={
            None: SourcePage((record("a"),), "page-2"),
            "page-2": SourcePage((record("b"),), "page-2"),
        },
        requested_cursors=[],
    )

    with pytest.raises(AdapterError, match="cursor repeated"):
        list(adapter.iter_records("110000"))


def test_adapter_rejects_non_positive_limit() -> None:
    adapter = PagedAdapter(pages={}, requested_cursors=[])

    with pytest.raises(ValueError, match="limit"):
        list(adapter.iter_records("110000", limit=0))
