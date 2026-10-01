from __future__ import annotations

import httpx
import pytest

from eye_collector.exceptions import HttpRequestError
from eye_collector.http import HttpClient


def build_client(
    transport: httpx.MockTransport,
    sleeps: list[float],
    *,
    attempts: int = 4,
    random_value: float = 1.0,
) -> HttpClient:
    now = [0.0]

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    return HttpClient(
        timeout_seconds=1,
        max_response_bytes=1024,
        max_attempts=attempts,
        backoff_base_seconds=0.5,
        user_agent="collector-tests/1.0",
        transport=transport,
        sleeper=sleeper,
        clock=lambda: now[0],
        random_uniform=lambda _low, high: high * random_value,
    )


def test_retries_429_and_honors_capped_retry_after() -> None:
    statuses = iter([429, 200])
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(statuses)
        headers = {"Retry-After": "120"} if status == 429 else {}
        return httpx.Response(status, headers=headers, json={"ok": True}, request=request)

    client = build_client(httpx.MockTransport(handler), sleeps)
    with client:
        response = client.get(
            "https://source.example.test/list", source_key="source-a", requests_per_second=100
        )

    assert response.status_code == 200
    assert sleeps == [30.0]


def test_retries_500_then_succeeds() -> None:
    statuses = iter([500, 200])
    sleeps: list[float] = []
    client = build_client(
        httpx.MockTransport(
            lambda request: httpx.Response(
                next(statuses), json={"ok": True}, request=request
            )
        ),
        sleeps,
    )

    with client:
        response = client.get(
            "https://source.example.test/list", source_key="source-a", requests_per_second=100
        )

    assert response.status_code == 200
    assert sleeps == [0.5]


def test_retries_timeout_and_stops_at_max_attempts() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=request)

    client = build_client(httpx.MockTransport(handler), sleeps, attempts=3)
    with client, pytest.raises(HttpRequestError, match="3 attempts"):
        client.get(
            "https://source.example.test/list", source_key="source-a", requests_per_second=100
        )

    assert calls == 3
    assert sleeps == [0.5, 1.0]


def test_retries_connection_reset() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("connection reset", request=request)
        return httpx.Response(200, content=b"ok", request=request)

    client = build_client(httpx.MockTransport(handler), sleeps)
    with client:
        response = client.get(
            "https://source.example.test/list", source_key="source-a", requests_per_second=100
        )

    assert response.status_code == 200
    assert calls == 2
    assert sleeps == [0.5]


def test_does_not_retry_404() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, request=request)

    client = build_client(httpx.MockTransport(handler), sleeps)
    with client, pytest.raises(HttpRequestError, match="HTTP 404"):
        client.get("https://source.example.test/missing", source_key="source-a")

    assert calls == 1
    assert sleeps == []


def test_does_not_retry_401() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, request=request)

    client = build_client(httpx.MockTransport(handler), [])
    with client, pytest.raises(HttpRequestError, match="HTTP 401"):
        client.get("https://source.example.test/list", source_key="source-a")

    assert calls == 1


@pytest.mark.parametrize("status", [400, 403])
def test_does_not_retry_forbidden_or_bad_requests(status: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, request=request)

    client = build_client(httpx.MockTransport(handler), [])
    with client, pytest.raises(HttpRequestError, match=f"HTTP {status}"):
        client.get("https://source.example.test/list", source_key="source-a")

    assert calls == 1
