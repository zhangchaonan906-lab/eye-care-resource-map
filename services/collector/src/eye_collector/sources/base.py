from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from eye_collector.exceptions import AdapterError
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage


class SourceAdapter(ABC):
    """Adapter contract for fetching source pages without transforming raw fields."""

    @property
    @abstractmethod
    def descriptor(self) -> SourceDescriptor:
        """Stable adapter key and source catalog metadata."""

    @abstractmethod
    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        """Fetch and parse one page through the injected shared HTTP client."""

    def iter_records(self, region_code: str, limit: int | None = None) -> Iterator[RawRecord]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")

        cursor: str | None = None
        seen_cursors: set[str] = set()
        yielded = 0
        while True:
            page = self.fetch_page(region_code, cursor)
            for record in page.records:
                if limit is not None and yielded >= limit:
                    return
                yielded += 1
                yield record

            next_cursor = page.next_cursor
            if next_cursor is None:
                return
            if next_cursor == cursor or next_cursor in seen_cursors:
                raise AdapterError("source page cursor repeated")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
