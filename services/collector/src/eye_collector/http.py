from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from eye_collector.exceptions import HttpRequestError, ResponseTooLargeError
from eye_collector.logging_utils import safe_log_origin

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRY_AFTER_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class HttpResult:
    status_code: int
    headers: Mapping[str, str]
    content: bytes


class _SourceRateLimiter:
    def __init__(
        self,
        clock: Callable[[], float],
        sleeper: Callable[[float], None],
    ) -> None:
        self._clock = clock
        self._sleeper = sleeper
        self._next_allowed: dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, source_key: str, requests_per_second: float, min_delay_ms: int) -> None:
        if requests_per_second <= 0 or min_delay_ms < 0:
            raise ValueError("source rate limit must be positive and min_delay_ms non-negative")
        interval = max(1.0 / requests_per_second, min_delay_ms / 1000.0)
        with self._lock:
            now = self._clock()
            scheduled_at = max(now, self._next_allowed.get(source_key, now))
            wait_seconds = scheduled_at - now
            self._next_allowed[source_key] = scheduled_at + interval
        if wait_seconds > 0:
            self._sleeper(wait_seconds)


class HttpClient:
    """Shared bounded HTTPS client with retries and per-source rate limiting."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_response_bytes: int,
        max_attempts: int,
        backoff_base_seconds: float,
        user_agent: str,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        random_uniform: Callable[[float, float], float] = random.uniform,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        if not 1 <= max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if backoff_base_seconds < 0:
            raise ValueError("backoff_base_seconds must be non-negative")
        if not user_agent or "\n" in user_agent or "\r" in user_agent:
            raise ValueError("user_agent must be a non-empty single-line value")

        self._max_response_bytes = max_response_bytes
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._sleeper = sleeper
        self._clock = clock
        self._random_uniform = random_uniform
        self._rate_limiter = _SourceRateLimiter(clock, sleeper)
        self._logger = logging.getLogger("eye_collector.http")
        self._log_context: dict[str, object] = {}
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def set_log_context(
        self,
        *,
        run_id: str,
        source_id: str,
        source_name: str,
        region_code: str,
    ) -> None:
        self._log_context = {
            "run_id": run_id,
            "source_id": source_id,
            "source_name": source_name,
            "region_code": region_code,
        }

    def get(
        self,
        url: str,
        *,
        source_key: str,
        requests_per_second: float = 1.0,
        min_delay_ms: int = 0,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResult:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise HttpRequestError("only HTTPS source URLs are allowed")
        if parsed.username is not None or parsed.password is not None:
            raise HttpRequestError("source URL must not contain credentials")

        for attempt in range(1, self._max_attempts + 1):
            self._rate_limiter.acquire(source_key, requests_per_second, min_delay_ms)
            try:
                with self._client.stream("GET", url, headers=headers) as response:
                    status_code = response.status_code
                    self._log_attempt(source_key, attempt, status_code, url)
                    if status_code in _RETRYABLE_STATUS:
                        if attempt == self._max_attempts:
                            raise HttpRequestError(
                                f"HTTP {status_code} after {self._max_attempts} attempts"
                            )
                        retry_after = self._retry_after(response.headers)
                        response.close()
                        self._sleep_before_retry(attempt, retry_after)
                        continue
                    if status_code < 200 or status_code >= 300:
                        raise HttpRequestError(f"HTTP {status_code}")

                    length = response.headers.get("content-length")
                    if (
                        length is not None
                        and length.isdigit()
                        and int(length) > self._max_response_bytes
                    ):
                        raise ResponseTooLargeError("response exceeds configured byte limit")

                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self._max_response_bytes:
                            raise ResponseTooLargeError("response exceeds configured byte limit")
                    return HttpResult(
                        status_code=status_code,
                        headers=dict(response.headers),
                        content=bytes(body),
                    )
            except ResponseTooLargeError:
                raise
            except HttpRequestError:
                raise
            except httpx.TransportError as error:
                self._logger.warning(
                    "http_transport_error",
                    extra={
                        "event": "http_transport_error",
                        "source_key": source_key,
                        "request_attempt": attempt,
                        "http_status": None,
                        "url": self._safe_url(url),
                        "error": type(error).__name__,
                        **self._log_context,
                    },
                )
                if attempt == self._max_attempts:
                    raise HttpRequestError(
                        f"request failed after {self._max_attempts} attempts "
                        f"({type(error).__name__})"
                    ) from error
                self._sleep_before_retry(attempt, None)

        raise HttpRequestError("request exhausted retry budget")

    def _sleep_before_retry(self, attempt: int, retry_after: float | None) -> None:
        exponential = min(
            _MAX_RETRY_AFTER_SECONDS,
            self._backoff_base_seconds * (2 ** (attempt - 1)),
        )
        delay = self._random_uniform(0.0, exponential)
        if retry_after is not None:
            delay = max(delay, min(retry_after, _MAX_RETRY_AFTER_SECONDS))
        if delay > 0:
            self._sleeper(delay)

    @staticmethod
    def _retry_after(headers: Mapping[str, str]) -> float | None:
        value = headers.get("retry-after")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None

    def _log_attempt(self, source_key: str, attempt: int, status_code: int, url: str) -> None:
        self._logger.info(
            "http_request",
            extra={
                "event": "http_request",
                "source_key": source_key,
                "request_attempt": attempt,
                "http_status": status_code,
                "url": self._safe_url(url),
                **self._log_context,
            },
        )

    @staticmethod
    def _safe_url(url: str) -> str:
        return safe_log_origin(url)
