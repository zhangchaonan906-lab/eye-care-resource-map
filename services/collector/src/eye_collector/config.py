from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

_DEFAULT_USER_AGENT = "eye-care-resource-collector/0.1"


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _float_env(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class CollectorConfig:
    database_url: str
    http_timeout_seconds: float = 10.0
    http_max_response_bytes: int = 1_048_576
    http_max_attempts: int = 4
    http_backoff_base_seconds: float = 0.25
    http_user_agent: str = _DEFAULT_USER_AGENT

    @classmethod
    def from_env(cls) -> CollectorConfig:
        database_url = os.getenv("DATABASE_URL", "").strip()
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")

        user_agent = os.getenv("HTTP_USER_AGENT", _DEFAULT_USER_AGENT).strip()
        if not user_agent or "\n" in user_agent or "\r" in user_agent:
            raise ValueError("HTTP_USER_AGENT must be a non-empty single-line value")

        return cls(
            database_url=database_url,
            http_timeout_seconds=_float_env(
                "HTTP_TIMEOUT_SECONDS", 10.0, minimum=0.1, maximum=120.0
            ),
            http_max_response_bytes=_int_env(
                "HTTP_MAX_RESPONSE_BYTES", 1_048_576, minimum=1, maximum=10_485_760
            ),
            http_max_attempts=_int_env("HTTP_MAX_ATTEMPTS", 4, minimum=1, maximum=5),
            http_backoff_base_seconds=_float_env(
                "HTTP_BACKOFF_BASE_SECONDS", 0.25, minimum=0.0, maximum=30.0
            ),
            http_user_agent=user_agent,
        )
