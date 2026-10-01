from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import RawRecord, SourceRegistration


class SourcePolicy:
    """Fail-closed authorization for source access and fields."""

    def authorize(self, source: SourceRegistration | None) -> None:
        if source is None:
            raise SourcePolicyError("source is not registered")
        if source.status != "approved":
            raise SourcePolicyError("source status must be approved")
        if not source.use_basis.strip():
            raise SourcePolicyError("source use_basis must be recorded")
        if not source.permitted_fields:
            raise SourcePolicyError("source permitted_fields must not be empty")
        if source.access_policy != "automated_access_allowed":
            raise SourcePolicyError("source access_policy does not allow automated access")

    def authorize_payload(
        self, source: SourceRegistration, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        self.authorize(source)
        unexpected = set(payload).difference(source.permitted_fields)
        if unexpected:
            fields = ", ".join(sorted(unexpected))
            raise SourcePolicyError(f"payload contains unpermitted fields: {fields}")
        if not isinstance(payload, dict):
            raise SourcePolicyError("raw payload must be a JSON object")
        return payload

    def authorize_record(self, source: SourceRegistration, record: RawRecord) -> RawRecord:
        self.authorize(source)
        if self._https_origin(source.url) != self._https_origin(record.source_url):
            raise SourcePolicyError("record URL must use the approved source origin")
        self.authorize_payload(source, record.raw_payload)
        return record

    @staticmethod
    def _https_origin(url: str) -> tuple[str, str, int]:
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("invalid HTTPS origin")
            return parsed.scheme, parsed.hostname.lower(), parsed.port or 443
        except ValueError as error:
            raise SourcePolicyError("record URL must use the approved source origin") from error
