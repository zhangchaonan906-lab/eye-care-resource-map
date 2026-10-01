from __future__ import annotations

import pytest

from eye_collector.geocoding.models import (
    CoordinateSystem,
    GeocodeErrorCode,
    GeocodeResult,
    GeocodeStatus,
    PrecisionLevel,
    ValidationStatus,
)
from eye_collector.geocoding.validation import validate_result

_PARENTS = {
    "110000": None,
    "110100": "110000",
    "110105": "110100",
    "310000": None,
    "310100": "310000",
    "310101": "310100",
}


def result(
    longitude: float | None = 116.397,
    latitude: float | None = 39.908,
    *,
    returned_adcode: str | None = "110105",
    precision: PrecisionLevel = PrecisionLevel.ROOFTOP,
    coordinate_system: CoordinateSystem = CoordinateSystem.WGS84,
    status: GeocodeStatus = GeocodeStatus.SUCCESS,
    accuracy_m: int | None = 20,
) -> GeocodeResult:
    return GeocodeResult(
        provider_record_id="fixture-point",
        longitude=longitude,
        latitude=latitude,
        original_coordinate_system=coordinate_system,
        precision_level=precision,
        result_type="point",
        returned_address="Synthetic address",
        returned_adcode=returned_adcode,
        accuracy_m=accuracy_m,
        status=status,
    )


def test_exact_high_precision_region_match_is_verified() -> None:
    checked = validate_result(result(), "110105", _PARENTS)

    assert checked.status is ValidationStatus.VERIFIED
    assert checked.error_code is None
    assert checked.longitude_wgs84 == 116.397


@pytest.mark.parametrize("returned_code", ["110100", "110000"])
def test_returned_parent_region_is_hierarchy_consistent(returned_code: str) -> None:
    checked = validate_result(result(returned_adcode=returned_code), "110105", _PARENTS)

    assert checked.status is ValidationStatus.VERIFIED


def test_unrelated_region_codes_are_rejected() -> None:
    checked = validate_result(result(returned_adcode="310101"), "110105", _PARENTS)

    assert checked.status is ValidationStatus.REJECTED
    assert checked.error_code is GeocodeErrorCode.REGION_MISMATCH


@pytest.mark.parametrize(
    "precision",
    [PrecisionLevel.DISTRICT, PrecisionLevel.CITY, PrecisionLevel.UNKNOWN],
)
def test_low_precision_is_never_verified(precision: PrecisionLevel) -> None:
    checked = validate_result(result(precision=precision), "110105", _PARENTS)

    assert checked.status is ValidationStatus.NEEDS_REVIEW
    assert checked.error_code is GeocodeErrorCode.LOW_PRECISION


@pytest.mark.parametrize("accuracy_m", [None, -1, 101])
def test_missing_or_unusable_accuracy_requires_review(accuracy_m: int | None) -> None:
    checked = validate_result(result(accuracy_m=accuracy_m), "110105", _PARENTS)

    assert checked.status is ValidationStatus.NEEDS_REVIEW
    assert checked.error_code is GeocodeErrorCode.LOW_PRECISION


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [(-181.0, 39.9), (116.4, 91.0), (0.0, 0.0), (120.0, 10.0), (150.0, 40.0)],
)
def test_invalid_world_china_and_null_island_coordinates_are_rejected(
    longitude: float, latitude: float
) -> None:
    checked = validate_result(result(longitude, latitude), "110105", _PARENTS)

    assert checked.status is ValidationStatus.REJECTED
    assert checked.error_code is GeocodeErrorCode.INVALID_COORDINATE
    assert checked.longitude_wgs84 is None


def test_missing_or_unknown_region_is_reviewed_without_name_comparison() -> None:
    checked = validate_result(result(returned_adcode="999999"), "110105", _PARENTS)

    assert checked.status is ValidationStatus.NEEDS_REVIEW
    assert checked.error_code is GeocodeErrorCode.REGION_MISMATCH


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (GeocodeStatus.NO_RESULT, GeocodeErrorCode.NO_RESULT),
        (GeocodeStatus.AMBIGUOUS, GeocodeErrorCode.AMBIGUOUS_RESULT),
    ],
)
def test_semantic_provider_results_go_to_review(
    status: GeocodeStatus, error: GeocodeErrorCode
) -> None:
    checked = validate_result(result(status=status), "110105", _PARENTS)

    assert checked.status is ValidationStatus.NEEDS_REVIEW
    assert checked.error_code is error


def test_gcj02_metadata_is_converted_before_validation() -> None:
    checked = validate_result(
        result(
            116.403963,
            39.915119,
            coordinate_system=CoordinateSystem.GCJ02,
        ),
        "110105",
        _PARENTS,
    )

    assert checked.status is ValidationStatus.VERIFIED
    assert checked.longitude_wgs84 != 116.403963


def test_missing_coordinate_is_rejected_as_malformed() -> None:
    checked = validate_result(result(None, None), "110105", _PARENTS)

    assert checked.status is ValidationStatus.REJECTED
    assert checked.error_code is GeocodeErrorCode.INVALID_COORDINATE
