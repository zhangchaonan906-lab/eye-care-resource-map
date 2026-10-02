from __future__ import annotations

from dataclasses import dataclass

import httpx
import psycopg

from eye_collector.exceptions import (
    AdapterConfigError,
    AdapterError,
    ETLFailedError,
    HttpRequestError,
    SourcePolicyError,
    TaskTimeoutError,
)


@dataclass(frozen=True, slots=True)
class FailureClass:
    code: str
    retryable: bool


def classify_failure(error: Exception) -> FailureClass:
    if isinstance(error, ETLFailedError):
        return FailureClass("ETL_FAILED", True)
    if isinstance(error, TaskTimeoutError):
        return FailureClass("TASK_TIMEOUT", True)
    if isinstance(error, SourcePolicyError):
        return FailureClass("POLICY_BLOCKED", False)
    if isinstance(error, AdapterConfigError):
        return FailureClass("ADAPTER_CONFIG_INVALID", False)
    if isinstance(error, AdapterError):
        return FailureClass("SCHEMA_CHANGED", False)
    if isinstance(error, psycopg.OperationalError):
        return FailureClass("DATABASE_TRANSIENT", True)
    if isinstance(error, httpx.TimeoutException):
        return FailureClass("NETWORK_TIMEOUT", True)
    if isinstance(error, HttpRequestError):
        message = str(error)
        if "HTTP 401" in message or "HTTP 403" in message:
            return FailureClass("ACCESS_FORBIDDEN", False)
        if "HTTP 429" in message:
            return FailureClass("HTTP_429", True)
        if "HTTP 5" in message:
            return FailureClass("HTTP_5XX", True)
        if "Timeout" in message or "timeout" in message.lower():
            return FailureClass("NETWORK_TIMEOUT", True)
        return FailureClass("COLLECTION_FAILED", False)
    return FailureClass("COLLECTION_FAILED", False)
