from __future__ import annotations

import pytest

from eye_collector.exceptions import (
    AdapterConfigError,
    AdapterError,
    HttpRequestError,
    SourcePolicyError,
    TaskTimeoutError,
)
from eye_collector.sync.failures import classify_failure


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TaskTimeoutError("deadline exceeded"), ("TASK_TIMEOUT", True)),
        (HttpRequestError("HTTP 429 after retries"), ("HTTP_429", True)),
        (HttpRequestError("HTTP 503 after retries"), ("HTTP_5XX", True)),
        (
            HttpRequestError("request failed after attempts (ReadTimeout)"),
            ("NETWORK_TIMEOUT", True),
        ),
        (SourcePolicyError("source is no longer approved"), ("POLICY_BLOCKED", False)),
        (AdapterConfigError("adapter key is not registered"), ("ADAPTER_CONFIG_INVALID", False)),
        (AdapterError("response schema changed"), ("SCHEMA_CHANGED", False)),
        (HttpRequestError("HTTP 403"), ("ACCESS_FORBIDDEN", False)),
        (ValueError("invalid schedule configuration"), ("COLLECTION_FAILED", False)),
    ],
)
def test_failure_classification_distinguishes_retryable_and_terminal_errors(
    error: Exception, expected: tuple[str, bool]
) -> None:
    classified = classify_failure(error)

    assert (classified.code, classified.retryable) == expected
