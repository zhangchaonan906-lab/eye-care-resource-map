from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator

from eye_collector.exceptions import AdapterError
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage, SourceRegistration


class SourceAdapter(ABC):
    """Adapter contract for fetching source pages without transforming raw fields."""

    @property
    @abstractmethod
    def descriptor(self) -> SourceDescriptor:
        """Stable adapter key and source catalog metadata."""

    @abstractmethod
    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        """Fetch and parse one page through the injected shared HTTP client."""

    def set_request_context(
        self,
        *,
        run_id: str,
        source: SourceRegistration,
        region_code: str,
    ) -> None:
        """Bind safe run metadata to HTTP logs when the adapter uses network requests."""
        return None

    def iter_pages(
        self,
        region_code: str,
        limit: int | None = None,
        *,
        on_request: Callable[[], None] | None = None,
    ) -> Iterator[SourcePage]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")

        cursor: str | None = None
        seen_cursors: set[str] = set()
        received = 0
        while True:
            if on_request is not None:
                on_request()
            page = self.fetch_page(region_code, cursor)
            received += len(page.records)
            yield page
            if limit is not None and received >= limit:
                return
            next_cursor = page.next_cursor
            if next_cursor is None:
                return
            if next_cursor == cursor or next_cursor in seen_cursors:
                raise AdapterError("source page cursor repeated")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def iter_records(self, region_code: str, limit: int | None = None) -> Iterator[RawRecord]:
        yielded = 0
        for page in self.iter_pages(region_code, limit):
            for record in page.records:
                if limit is not None and yielded >= limit:
                    return
                yielded += 1
                yield record
