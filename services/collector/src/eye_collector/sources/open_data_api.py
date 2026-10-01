from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit

from eye_collector.exceptions import AdapterError
from eye_collector.hashing import canonical_sha256
from eye_collector.http import HttpClient
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage, SourceRegistration
from eye_collector.sources.base import SourceAdapter


@dataclass(frozen=True, slots=True)
class OpenDataApiDataset:
    source_key: str
    source_name: str
    dataset_url: str
    endpoint_url: str
    expected_fields: tuple[str, ...]
    field_mapping: tuple[tuple[str, str], ...]
    stable_key_field: str
    records_key: str
    next_cursor_key: str | None = None
    cursor_parameter: str = "cursor"
    page_size: int = 50
    headers: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        expected = set(self.expected_fields)
        mapped = [source_field for source_field, _canonical in self.field_mapping]
        if not self.source_key or not self.source_name:
            raise ValueError("source key and name are required")
        if not self.expected_fields or len(expected) != len(self.expected_fields):
            raise ValueError("expected API fields must be non-empty and unique")
        if set(mapped) != expected or len(mapped) != len(expected):
            raise ValueError("API field mapping must explicitly map every expected field")
        if self.stable_key_field not in expected:
            raise ValueError("stable key field must be present in expected API fields")
        if not 1 <= self.page_size <= 150:
            raise ValueError("API page_size must be between 1 and 150")
        dataset_origin = _https_origin(self.dataset_url)
        endpoint_origin = _https_origin(self.endpoint_url)
        if dataset_origin != endpoint_origin:
            raise ValueError("API endpoint must use the same HTTPS origin as the dataset page")
        if not self.records_key or not self.cursor_parameter:
            raise ValueError("API record and cursor keys must be non-empty")


class OpenDataApiAdapter(SourceAdapter):
    """Fetch an approved JSON API using explicit schema and field mappings.

    This adapter performs no approval itself: the existing SourcePolicy must authorize
    its descriptor as an automated HTTP source before any record is persisted.
    """

    def __init__(self, http: HttpClient, dataset: OpenDataApiDataset) -> None:
        self._http = http
        self._dataset = dataset

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            source_key=self._dataset.source_key,
            source_name=self._dataset.source_name,
            catalog_url=self._dataset.dataset_url,
            access_method="http",
        )

    def set_request_context(
        self,
        *,
        run_id: str,
        source: SourceRegistration,
        region_code: str,
    ) -> None:
        self._http.set_log_context(
            run_id=run_id,
            source_id=source.id,
            source_name=source.name,
            region_code=region_code,
        )

    def fetch_page(self, region_code: str, cursor: str | None) -> SourcePage:
        if len(region_code) != 6 or not region_code.isdigit():
            raise ValueError("region_code must contain six digits")
        query: dict[str, str | int] = {"region": region_code, "limit": self._dataset.page_size}
        if cursor is not None:
            query[self._dataset.cursor_parameter] = cursor
        result = self._http.get(
            f"{self._dataset.endpoint_url}?{urlencode(query)}",
            source_key=self._dataset.source_key,
            requests_per_second=1.0,
            min_delay_ms=0,
            max_concurrency=1,
            headers=self._dataset.headers,
        )
        try:
            body = json.loads(result.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("open-data API response is not valid JSON") from error
        if not isinstance(body, dict) or not isinstance(body.get(self._dataset.records_key), list):
            raise AdapterError("open-data API response does not match its approved envelope")

        records: list[RawRecord] = []
        for item in body[self._dataset.records_key]:
            if not isinstance(item, dict) or set(item) != set(self._dataset.expected_fields):
                raise AdapterError("open-data API record schema changed from the approved mapping")
            source_fields = {key: _string_value(item[key]) for key in self._dataset.expected_fields}
            mapped = {
                canonical: source_fields[source]
                for source, canonical in self._dataset.field_mapping
                if source_fields[source] is not None
            }
            name = mapped.get("name")
            if not isinstance(name, str) or not name.strip():
                raise AdapterError("open-data API record is missing a required hospital name")
            source_key = source_fields.get(self._dataset.stable_key_field)
            if not source_key:
                source_key = canonical_sha256(source_fields)
            records.append(
                RawRecord(
                    source_key,
                    self._dataset.dataset_url,
                    {"source_fields": source_fields, **mapped},
                )
            )

        next_cursor: Any = None
        if self._dataset.next_cursor_key is not None:
            next_cursor = body.get(self._dataset.next_cursor_key)
            if next_cursor is not None and not isinstance(next_cursor, str):
                raise AdapterError("open-data API cursor must be a string or null")
        return SourcePage(tuple(records), next_cursor)


def _string_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _https_origin(url: str) -> tuple[str, str, int]:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("URL must be HTTPS without credentials")
        return parsed.scheme, parsed.hostname.lower(), parsed.port or 443
    except ValueError as error:
        raise ValueError("URL must be HTTPS without credentials") from error
