from __future__ import annotations


class CollectorError(Exception):
    """Base class for expected collector failures."""


class SourcePolicyError(CollectorError):
    """Raised when a source or one of its fields is not approved for collection."""


class AdapterError(CollectorError):
    """Raised when an adapter cannot produce a valid source page."""


class AdapterConfigError(CollectorError):
    """Raised when a sync task names an adapter absent from the code registry."""


class TaskTimeoutError(CollectorError):
    """Raised when an incremental sync exceeds its configured monotonic deadline."""


class ETLFailedError(CollectorError):
    """Raised when scoped ETL returns one or more processing errors."""


class HttpRequestError(CollectorError):
    """Raised for non-retryable or exhausted HTTP requests."""


class ResponseTooLargeError(HttpRequestError):
    """Raised when an upstream response exceeds the configured size bound."""
