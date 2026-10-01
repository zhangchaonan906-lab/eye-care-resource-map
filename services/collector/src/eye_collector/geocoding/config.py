from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from eye_collector.config import _float_env, _int_env


@dataclass(frozen=True, slots=True)
class GeocodingConfig:
    database_url: str
    http_timeout_seconds: float
    http_max_response_bytes: int
    http_max_attempts: int
    http_backoff_base_seconds: float
    http_user_agent: str

    @classmethod
    def from_env(cls) -> GeocodingConfig:
        database_url = os.getenv("GEOCODE_DATABASE_URL", "").strip()
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise ValueError("GEOCODE_DATABASE_URL must be a PostgreSQL connection URL")
        user_agent = os.getenv("HTTP_USER_AGENT", "eye-care-resource-geocoder/0.1").strip()
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
