from __future__ import annotations


class CollectorError(Exception):
    """Base class for expected collector failures."""


class SourcePolicyError(CollectorError):
    """Raised when a source or one of its fields is not approved for collection."""


class AdapterError(CollectorError):
    """Raised when an adapter cannot produce a valid source page."""


class HttpRequestError(CollectorError):
    """Raised for non-retryable or exhausted HTTP requests."""


class ResponseTooLargeError(HttpRequestError):
    """Raised when an upstream response exceeds the configured size bound."""
