from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import SourceRegistration


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
