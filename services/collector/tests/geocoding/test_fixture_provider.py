from __future__ import annotations

import pytest

from eye_collector.geocoding.models import (
    CoordinateSystem,
    GeocodeErrorCode,
    GeocodeStatus,
    PrecisionLevel,
)
from eye_collector.geocoding.providers.fixture import (
    FixtureGeocoder,
    FixtureGeocodeTransport,
    GeocodeProviderError,
)
from eye_collector.http import HttpClient


def make_provider(
    *, scenario: str = "normal", quota_per_run: int = 100
) -> tuple[FixtureGeocoder, FixtureGeocodeTransport]:
    transport = FixtureGeocodeTransport(scenario=scenario)
    client = HttpClient(
        timeout_seconds=0.1,
        max_response_bytes=16_384,
        max_attempts=2,
        backoff_base_seconds=0,
        user_agent="synthetic-geocoder-test/1.0",
        transport=transport,
        sleeper=lambda _seconds: None,
        clock=lambda: 0,
        random_uniform=lambda _low, _high: 0,
    )
    return FixtureGeocoder(client, quota_per_run=quota_per_run), transport


def test_fixture_provider_sends_address_and_administrative_code() -> None:
    provider, transport = make_provider()
    try:
        result = provider.geocode("Fixture Rooftop", "110105")
    finally:
        provider.close()

    assert transport.requests == [("Fixture Rooftop", "110105")]
    assert result.longitude == 116.397
    assert result.original_coordinate_system is CoordinateSystem.WGS84
    assert result.precision_level is PrecisionLevel.ROOFTOP


def test_fixture_provider_preserves_gcj02_metadata() -> None:
    provider, _transport = make_provider()
    try:
        result = provider.geocode("Fixture GCJ", "110105")
    finally:
        provider.close()

    assert result.original_coordinate_system is CoordinateSystem.GCJ02
    assert result.longitude == 116.403963


def test_fixture_provider_reuses_http_client_retry_for_429() -> None:
    provider, transport = make_provider(scenario="retry_429")
    try:
        result = provider.geocode("Fixture Rooftop", "110105")
    finally:
        provider.close()

    assert result.status is GeocodeStatus.SUCCESS
    assert transport.attempt_count == 2


def test_fixture_provider_reuses_http_client_retry_for_timeout() -> None:
    provider, transport = make_provider(scenario="timeout")
    try:
        result = provider.geocode("Fixture Rooftop", "110105")
    finally:
        provider.close()

    assert result.status is GeocodeStatus.SUCCESS
    assert transport.attempt_count == 2


@pytest.mark.parametrize(
    ("address", "status", "error_code"),
    [
        ("Fixture No Result", GeocodeStatus.NO_RESULT, GeocodeErrorCode.NO_RESULT),
        ("Fixture Ambiguous", GeocodeStatus.AMBIGUOUS, GeocodeErrorCode.AMBIGUOUS_RESULT),
    ],
)
def test_semantic_results_return_once_without_retry(
    address: str, status: GeocodeStatus, error_code: GeocodeErrorCode
) -> None:
    provider, transport = make_provider()
    try:
        result = provider.geocode(address, "110105")
    finally:
        provider.close()

    assert result.status is status
    assert result.error_code is error_code
    assert transport.attempt_count == 1


def test_provider_run_quota_stops_calls_before_http_request() -> None:
    provider, transport = make_provider(quota_per_run=1)
    try:
        provider.geocode("Fixture Rooftop", "110105")
        with pytest.raises(GeocodeProviderError) as error:
            provider.geocode("Fixture Rooftop", "110105")
    finally:
        provider.close()

    assert error.value.code is GeocodeErrorCode.RATE_LIMITED
    assert transport.attempt_count == 1


def test_retried_http_rate_limit_is_typed_when_budget_is_exhausted() -> None:
    provider, _transport = make_provider(scenario="always_429")
    try:
        with pytest.raises(GeocodeProviderError) as error:
            provider.geocode("Fixture Rooftop", "110105")
    finally:
        provider.close()

    assert error.value.code is GeocodeErrorCode.RATE_LIMITED
