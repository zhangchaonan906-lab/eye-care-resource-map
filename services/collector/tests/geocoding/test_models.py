from __future__ import annotations

import pytest

from eye_collector.geocoding.models import (
    CoordinateSystem,
    GeocodeErrorCode,
    GeocodeResult,
    GeocodeStatus,
    PrecisionLevel,
    ProviderPolicy,
)


def test_provider_policy_requires_explicit_persistence_decision_and_quota() -> None:
    blocked = ProviderPolicy(
        provider="unapproved",
        version="1",
        persistent_storage_allowed=False,
        quota_per_run=0,
    )
    fixture = ProviderPolicy(
        provider="fixture",
        version="1",
        persistent_storage_allowed=True,
        quota_per_run=10,
    )

    assert blocked.persistent_storage_allowed is False
    assert blocked.quota_per_run == 0
    assert fixture.persistent_storage_allowed is True


def test_geocode_result_keeps_original_coordinate_system_and_error_category() -> None:
    result = GeocodeResult(
        provider_record_id="fixture-1",
        longitude=116.4,
        latitude=39.9,
        original_coordinate_system=CoordinateSystem.GCJ02,
        precision_level=PrecisionLevel.BUILDING,
        result_type="building",
        returned_address="Synthetic Road",
        returned_adcode="110105",
        accuracy_m=25,
        status=GeocodeStatus.SUCCESS,
    )

    assert result.original_coordinate_system is CoordinateSystem.GCJ02
    assert GeocodeErrorCode.REGION_MISMATCH.value == "REGION_MISMATCH"
    assert PrecisionLevel.DISTRICT.value == "district"
    assert result.status is GeocodeStatus.SUCCESS


def test_provider_policy_rejects_negative_quota() -> None:
    with pytest.raises(ValueError, match="quota"):
        ProviderPolicy(
            provider="fixture",
            version="1",
            persistent_storage_allowed=True,
            quota_per_run=-1,
        )
