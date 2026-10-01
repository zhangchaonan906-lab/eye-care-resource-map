from __future__ import annotations

import json
from importlib.resources import files
from typing import Any
from urllib.parse import parse_qs, urlencode

import httpx

from eye_collector.exceptions import AdapterError
from eye_collector.http import HttpClient
from eye_collector.models import RawRecord, SourceDescriptor, SourcePage, SourceRegistration
from eye_collector.sources.base import SourceAdapter

_CATALOG_URL = "https://fixture.invalid/directory"


class FixtureTransport(httpx.BaseTransport):
    """Serves packaged synthetic pages without opening a network connection."""

    def __init__(self, *, revision: str = "stable", scenario: str = "normal") -> None:
        if revision not in {"stable", "updated"}:
            raise ValueError("fixture revision must be stable or updated")
        if scenario not in {"normal", "retry_429", "retry_500", "timeout"}:
            raise ValueError("unsupported fixture HTTP scenario")
        self._revision = revision
        self._scenario = scenario
        self._attempts: dict[str, int] = {}

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.scheme != "https" or request.url.host != "fixture.invalid":
            raise AdapterError("fixture transport only serves fixture.invalid")
        if request.url.path != "/directory":
            return httpx.Response(404, request=request)

        query = parse_qs(request.url.query.decode("ascii"))
        if query.get("revision", ["stable"])[0] != self._revision:
            return httpx.Response(400, request=request)
        page_number = query.get("page", ["1"])[0]
        attempt_key = f"{page_number}:{self._revision}"
        self._attempts[attempt_key] = self._attempts.get(attempt_key, 0) + 1
        if self._scenario != "normal" and self._attempts[attempt_key] == 1:
            if self._scenario == "retry_429":
                return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
            if self._scenario == "retry_500":
                return httpx.Response(500, request=request)
            raise httpx.ReadTimeout("synthetic fixture timeout", request=request)

        if page_number == "1":
            fixture_name = "page-1-updated.json" if self._revision == "updated" else "page-1.json"
        elif page_number == "2":
            fixture_name = "page-2.json"
        else:
            return httpx.Response(404, request=request)

        fixture_path = files("eye_collector").joinpath("fixtures", "fixture", fixture_name)
        return httpx.Response(
            200,
            headers={"content-type": "application/json; charset=utf-8"},
            content=fixture_path.read_bytes(),
            request=request,
        )


class FixtureSourceAdapter(SourceAdapter):
    def __init__(self, http: HttpClient, *, revision: str = "stable") -> None:
        if revision not in {"stable", "updated"}:
            raise ValueError("fixture revision must be stable or updated")
        self._http = http
        self._revision = revision

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            source_key="fixture",
            source_name="Fixture Directory",
            catalog_url=_CATALOG_URL,
            requests_per_second=1.0,
            min_delay_ms=0,
            max_concurrency=1,
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
        if cursor not in {None, "page-2"}:
            raise AdapterError("fixture cursor is invalid")
        page_number = "1" if cursor is None else "2"
        query = urlencode(
            {"page": page_number, "region": region_code, "revision": self._revision}
        )
        result = self._http.get(
            f"{_CATALOG_URL}?{query}",
            source_key=self.descriptor.source_key,
            requests_per_second=self.descriptor.requests_per_second,
            min_delay_ms=self.descriptor.min_delay_ms,
        )
        try:
            data = json.loads(result.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("fixture page is not valid JSON") from error
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            raise AdapterError("fixture page must contain a records array")

        records: list[RawRecord] = []
        for item in data["records"]:
            if not isinstance(item, dict):
                raise AdapterError("fixture record must be a JSON object")
            source_key = item.get("source_key")
            source_url = item.get("source_url")
            raw_payload: Any = item.get("raw_payload")
            if (
                not isinstance(source_key, str)
                or not source_key
                or not isinstance(source_url, str)
                or not isinstance(raw_payload, dict)
            ):
                raise AdapterError("fixture record is missing its key, URL, or raw object")
            records.append(RawRecord(source_key, source_url, raw_payload))

        next_cursor = data.get("next_cursor")
        if next_cursor is not None and not isinstance(next_cursor, str):
            raise AdapterError("fixture next_cursor must be a string or null")
        return SourcePage(tuple(records), next_cursor)
