from __future__ import annotations

import math
from collections.abc import Mapping

from eye_collector.geocoding.coordinates import CoordinateConversionError, to_wgs84
from eye_collector.geocoding.models import (
    CoordinateValidation,
    GeocodeErrorCode,
    GeocodeResult,
    GeocodeStatus,
    PrecisionLevel,
    ValidationStatus,
)

_HIGH_PRECISION = {PrecisionLevel.ROOFTOP, PrecisionLevel.BUILDING}


def _is_ancestor(ancestor: str, code: str, parents: Mapping[str, str | None]) -> bool:
    seen: set[str] = set()
    current: str | None = code
    while current is not None and current not in seen:
        if current == ancestor:
            return True
        seen.add(current)
        current = parents.get(current)
    return False


def _regions_consistent(
    candidate_code: str | None,
    returned_code: str | None,
    parents: Mapping[str, str | None],
) -> bool | None:
    if (
        candidate_code is None
        or returned_code is None
        or candidate_code not in parents
        or returned_code not in parents
    ):
        return None
    return _is_ancestor(candidate_code, returned_code, parents) or _is_ancestor(
        returned_code, candidate_code, parents
    )


def _failure(
    status: ValidationStatus,
    code: GeocodeErrorCode,
    reason: str,
    longitude: float | None = None,
    latitude: float | None = None,
) -> CoordinateValidation:
    return CoordinateValidation(status, code, reason, longitude, latitude)


def validate_result(
    result: GeocodeResult,
    candidate_adcode: str | None,
    region_parents: Mapping[str, str | None],
) -> CoordinateValidation:
    if result.status is GeocodeStatus.NO_RESULT:
        return _failure(
            ValidationStatus.NEEDS_REVIEW,
            GeocodeErrorCode.NO_RESULT,
            "provider_no_result",
        )
    if result.status is GeocodeStatus.AMBIGUOUS:
        return _failure(
            ValidationStatus.NEEDS_REVIEW,
            GeocodeErrorCode.AMBIGUOUS_RESULT,
            "provider_returned_ambiguous_results",
        )
    if result.longitude is None or result.latitude is None:
        return _failure(
            ValidationStatus.REJECTED,
            GeocodeErrorCode.INVALID_COORDINATE,
            "coordinate_missing",
        )
    if (
        not math.isfinite(result.longitude)
        or not math.isfinite(result.latitude)
        or not -180 <= result.longitude <= 180
        or not -90 <= result.latitude <= 90
        or (abs(result.longitude) <= 0.01 and abs(result.latitude) <= 0.01)
    ):
        return _failure(
            ValidationStatus.REJECTED,
            GeocodeErrorCode.INVALID_COORDINATE,
            "coordinate_out_of_range_or_null_island",
        )
    try:
        longitude, latitude = to_wgs84(
            result.longitude, result.latitude, result.original_coordinate_system
        )
    except CoordinateConversionError:
        return _failure(
            ValidationStatus.REJECTED,
            GeocodeErrorCode.INVALID_COORDINATE,
            "coordinate_system_not_convertible",
        )
    if not (73.5 <= longitude <= 135.1 and 18.0 <= latitude <= 53.6):
        return _failure(
            ValidationStatus.REJECTED,
            GeocodeErrorCode.INVALID_COORDINATE,
            "coordinate_outside_china_bounds",
        )

    region_match = _regions_consistent(candidate_adcode, result.returned_adcode, region_parents)
    if region_match is False:
        return _failure(
            ValidationStatus.REJECTED,
            GeocodeErrorCode.REGION_MISMATCH,
            "returned_region_is_unrelated_to_candidate_region",
            longitude,
            latitude,
        )
    if region_match is None:
        return _failure(
            ValidationStatus.NEEDS_REVIEW,
            GeocodeErrorCode.REGION_MISMATCH,
            "candidate_or_returned_region_is_unknown",
            longitude,
            latitude,
        )
    if result.precision_level not in _HIGH_PRECISION:
        return _failure(
            ValidationStatus.NEEDS_REVIEW,
            GeocodeErrorCode.LOW_PRECISION,
            "provider_precision_below_building",
            longitude,
            latitude,
        )
    return CoordinateValidation(ValidationStatus.VERIFIED, None, None, longitude, latitude)
