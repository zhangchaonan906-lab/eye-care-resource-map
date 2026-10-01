from __future__ import annotations

import pytest

from eye_collector.config import CollectorConfig


def test_config_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        CollectorConfig.from_env()


def test_config_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/eye")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValueError, match="HTTP_TIMEOUT_SECONDS"):
        CollectorConfig.from_env()


def test_config_reads_database_and_http_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/eye")
    monkeypatch.setenv("HTTP_MAX_ATTEMPTS", "3")

    config = CollectorConfig.from_env()

    assert config.database_url == "postgresql://user:pass@localhost/eye"
    assert config.http_max_attempts == 3
    assert config.http_timeout_seconds == 10

