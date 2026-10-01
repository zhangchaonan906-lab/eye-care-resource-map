from __future__ import annotations

from dataclasses import replace

import pytest

from eye_collector.exceptions import SourcePolicyError
from eye_collector.models import RawRecord, SourceRegistration
from eye_collector.policy import SourcePolicy


@pytest.fixture
def approved_source() -> SourceRegistration:
    return SourceRegistration(
        id="00000000-0000-0000-0000-000000000001",
        name="Fixture Directory",
        url="https://fixture.invalid/directory",
        use_basis="Local synthetic fixture; no external rights asserted",
        permitted_fields=frozenset({"name", "address", "region", "updated_at"}),
        access_policy="automated_access_allowed",
        status="approved",
    )


def test_approved_source_is_allowed(approved_source: SourceRegistration) -> None:
    assert SourcePolicy().authorize(approved_source) is None


def test_manual_only_source_can_be_used_by_file_adapter(
    approved_source: SourceRegistration,
) -> None:
    source = replace(approved_source, access_policy="manual_only")

    assert SourcePolicy().authorize(source, access_method="file") is None


def test_manual_only_source_cannot_be_used_for_http(
    approved_source: SourceRegistration,
) -> None:
    source = replace(approved_source, access_policy="manual_only")

    with pytest.raises(SourcePolicyError, match="access method"):
        SourcePolicy().authorize(source, access_method="http")


@pytest.mark.parametrize("status", ["pending", "suspended"])
def test_non_approved_source_is_rejected_before_run(
    approved_source: SourceRegistration, status: str
) -> None:
    source = replace(approved_source, status=status)

    with pytest.raises(SourcePolicyError, match="approved"):
        SourcePolicy().authorize(source)


def test_unknown_source_is_rejected_before_run() -> None:
    with pytest.raises(SourcePolicyError, match="not registered"):
        SourcePolicy().authorize(None)


@pytest.mark.parametrize(
    "field, value",
    [
        ("use_basis", ""),
        ("permitted_fields", frozenset()),
        ("access_policy", "blocked"),
    ],
)
def test_missing_or_blocking_policy_fails_closed(
    approved_source: SourceRegistration, field: str, value: object
) -> None:
    source = replace(approved_source, **{field: value})

    with pytest.raises(SourcePolicyError):
        SourcePolicy().authorize(source)


def test_unpermitted_raw_field_rejects_whole_record(
    approved_source: SourceRegistration,
) -> None:
    payload = {"name": "Fixture Clinic", "address": "Somewhere", "email": "private@example.org"}

    with pytest.raises(SourcePolicyError, match="unpermitted fields"):
        SourcePolicy().authorize_payload(approved_source, payload)


def test_permitted_payload_is_not_rewritten(approved_source: SourceRegistration) -> None:
    payload = {"name": "Fixture Clinic", "address": "Somewhere", "region": "110000"}

    assert SourcePolicy().authorize_payload(approved_source, payload) is payload


@pytest.mark.parametrize(
    "url",
    [
        "http://fixture.invalid/facility/1",
        "https://other.invalid/facility/1",
        "https://user:pass@fixture.invalid/facility/1",
    ],
)
def test_record_url_must_remain_on_approved_https_origin(
    approved_source: SourceRegistration, url: str
) -> None:
    record = RawRecord("clinic-1", url, {"name": "Clinic"})

    with pytest.raises(SourcePolicyError, match="source origin"):
        SourcePolicy().authorize_record(approved_source, record)
