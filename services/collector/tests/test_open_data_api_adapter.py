from __future__ import annotations

import json

import httpx
import pytest

from eye_collector.exceptions import AdapterError
from eye_collector.http import HttpClient
from eye_collector.sources.open_data_api import OpenDataApiAdapter, OpenDataApiDataset


def adapter_for(payload: dict[str, object]) -> OpenDataApiAdapter:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "fixture.invalid"
        return httpx.Response(200, content=json.dumps(payload).encode(), request=request)

    http = HttpClient(
        timeout_seconds=1,
        max_response_bytes=1024 * 1024,
        max_attempts=1,
        backoff_base_seconds=0,
        user_agent="eye-map-test/1.0",
        transport=httpx.MockTransport(handler),
        sleeper=lambda _delay: None,
    )
    dataset = OpenDataApiDataset(
        source_key="sample-open-data-api",
        source_name="Sample official API",
        dataset_url="https://fixture.invalid/dataset",
        endpoint_url="https://fixture.invalid/api/hospitals",
        expected_fields=("id", "name", "address"),
        field_mapping=(("id", "source_reference_id"), ("name", "name"), ("address", "address")),
        stable_key_field="id",
        records_key="records",
        next_cursor_key="next",
        cursor_parameter="cursor",
        headers={"X-Api-Key": "not-logged"},
    )
    return OpenDataApiAdapter(http, dataset)


def test_api_adapter_maps_explicit_fields_and_paginates() -> None:
    adapter = adapter_for(
        {
            "records": [{"id": "001", "name": "测试医院", "address": "北京市东城区"}],
            "next": "page-2",
        }
    )

    page = adapter.fetch_page("110000", None)

    assert page.records[0].source_key == "001"
    assert page.records[0].raw_payload == {
        "source_fields": {"id": "001", "name": "测试医院", "address": "北京市东城区"},
        "source_reference_id": "001",
        "name": "测试医院",
        "address": "北京市东城区",
    }
    assert page.records[0].source_url == "https://fixture.invalid/dataset"
    assert page.next_cursor == "page-2"
    assert adapter.descriptor.access_method == "http"


def test_api_adapter_fails_closed_on_schema_change() -> None:
    adapter = adapter_for({"records": [{"id": "001", "name": "医院", "new": "字段"}]})

    with pytest.raises(AdapterError, match="schema"):
        adapter.fetch_page("110000", None)


def test_api_adapter_rejects_endpoint_outside_catalog_origin() -> None:
    with pytest.raises(ValueError, match="same HTTPS origin"):
        OpenDataApiDataset(
            source_key="sample",
            source_name="Sample",
            dataset_url="https://fixture.invalid/dataset",
            endpoint_url="https://other.invalid/api",
            expected_fields=("id", "name"),
            field_mapping=(("id", "source_reference_id"), ("name", "name")),
            stable_key_field="id",
            records_key="records",
        )
