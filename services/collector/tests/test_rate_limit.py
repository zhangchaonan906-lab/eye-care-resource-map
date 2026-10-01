from __future__ import annotations

import httpx

from eye_collector.http import HttpClient


def test_rate_limit_is_per_source_and_uses_the_stricter_delay() -> None:
    now = 0.0
    sleeps: list[float] = []
    requests: list[str] = []

    def sleep_for(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.host)
        return httpx.Response(200, content=b"ok", request=request)

    client = HttpClient(
        timeout_seconds=1,
        max_response_bytes=32,
        max_attempts=1,
        backoff_base_seconds=0,
        user_agent="collector-tests/1.0",
        transport=httpx.MockTransport(handler),
        sleeper=sleep_for,
        clock=lambda: now,
        random_uniform=lambda _low, _high: 0,
    )
    with client:
        client.get(
            "https://a.example.test/1",
            source_key="source-a",
            requests_per_second=4,
            min_delay_ms=400,
        )
        client.get(
            "https://a.example.test/2",
            source_key="source-a",
            requests_per_second=4,
            min_delay_ms=400,
        )
        client.get(
            "https://b.example.test/1",
            source_key="source-b",
            requests_per_second=4,
            min_delay_ms=400,
        )

    assert requests == ["a.example.test", "a.example.test", "b.example.test"]
    assert sleeps == [0.4]


def test_rate_limit_supports_per_source_minimum_delay() -> None:
    now = 0.0
    sleeps: list[float] = []

    def sleeper(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    client = HttpClient(
        timeout_seconds=1,
        max_response_bytes=32,
        max_attempts=1,
        backoff_base_seconds=0,
        user_agent="collector-tests/1.0",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"ok", request=request)
        ),
        sleeper=sleeper,
        clock=lambda: now,
        random_uniform=lambda _low, _high: 0,
    )
    with client:
        for _ in range(3):
            client.get(
                "https://a.example.test/",
                source_key="source-a",
                requests_per_second=10,
                min_delay_ms=250,
            )

    assert sleeps == [0.25, 0.25]
