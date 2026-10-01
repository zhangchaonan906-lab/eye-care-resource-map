from __future__ import annotations

import httpx
import pytest

from eye_collector.exceptions import HttpRequestError, ResponseTooLargeError
from eye_collector.http import HttpClient


def test_client_sets_user_agent_and_rejects_http_urls() -> None:
    seen_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        return httpx.Response(200, content=b"ok", request=request)

    client = HttpClient(
        timeout_seconds=1,
        max_response_bytes=8,
        max_attempts=1,
        backoff_base_seconds=0,
        user_agent="eye-map-test/1.0",
        transport=httpx.MockTransport(handler),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )
    with client:
        client.get(
            "https://source.example.test/list",
            source_key="source-a",
            headers={"X-Source-Version": "fixture-v1"},
        )
        with pytest.raises(HttpRequestError, match="HTTPS"):
            client.get("http://source.example.test/list", source_key="source-a")

    assert seen_headers[0]["user-agent"] == "eye-map-test/1.0"
    assert seen_headers[0]["x-source-version"] == "fixture-v1"


def test_client_rejects_url_credentials() -> None:
    client = HttpClient(
        timeout_seconds=1,
        max_response_bytes=8,
        max_attempts=1,
        backoff_base_seconds=0,
        user_agent="eye-map-test/1.0",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )
    with client, pytest.raises(HttpRequestError, match="credentials"):
        client.get("https://token:secret@source.example.test/list", source_key="source-a")


def test_response_body_is_bounded() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=b"0123456789", request=request)

    client = HttpClient(
        timeout_seconds=1,
        max_response_bytes=4,
        max_attempts=4,
        backoff_base_seconds=0,
        user_agent="eye-map-test/1.0",
        transport=httpx.MockTransport(handler),
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )
    with client, pytest.raises(ResponseTooLargeError):
        client.get("https://source.example.test/list", source_key="source-a")

    assert calls == 1
