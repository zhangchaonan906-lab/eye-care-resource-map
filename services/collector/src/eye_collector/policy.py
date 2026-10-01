from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import RawRecord, SourceRegistration


class SourcePolicy:
    """Fail-closed authorization for source access and fields."""

    def authorize(
        self, source: SourceRegistration | None, *, access_method: str = "http"
    ) -> None:
        if source is None:
            raise SourcePolicyError("source is not registered")
        if source.status != "approved":
            raise SourcePolicyError("source status must be approved")
        if not source.use_basis.strip():
            raise SourcePolicyError("source use_basis must be recorded")
        if not source.permitted_fields:
            raise SourcePolicyError("source permitted_fields must not be empty")
        permitted = {
            "http": "automated_access_allowed",
            "file": "manual_only",
        }.get(access_method)
        if permitted is None or source.access_policy != permitted:
            raise SourcePolicyError("source access method is not allowed by access_policy")

    def authorize_payload(
        self,
        source: SourceRegistration,
        payload: Mapping[str, Any],
        *,
        access_method: str = "http",
    ) -> dict[str, Any]:
        self.authorize(source, access_method=access_method)
        unexpected = set(payload).difference(source.permitted_fields)
        if unexpected:
            fields = ", ".join(sorted(unexpected))
            raise SourcePolicyError(f"payload contains unpermitted fields: {fields}")
        if not isinstance(payload, dict):
            raise SourcePolicyError("raw payload must be a JSON object")
        return payload

    def authorize_record(
        self, source: SourceRegistration, record: RawRecord, *, access_method: str = "http"
    ) -> RawRecord:
        self.authorize(source, access_method=access_method)
        if self._https_origin(source.url) != self._https_origin(record.source_url):
            raise SourcePolicyError("record URL must use the approved source origin")
        self.authorize_payload(source, record.raw_payload, access_method=access_method)
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
