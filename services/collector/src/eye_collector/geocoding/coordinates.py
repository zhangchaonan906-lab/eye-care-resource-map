from __future__ import annotations

import math

from eye_collector.geocoding.models import CoordinateSystem

_PI = math.pi
_AXIS = 6_378_245.0
_ECCENTRICITY_SQUARED = 0.00669342162296594323


class CoordinateConversionError(ValueError):
    """The input coordinate system cannot be converted to WGS84 safely."""


def _outside_china(longitude: float, latitude: float) -> bool:
    return not (73.5 <= longitude <= 135.1 and 18.0 <= latitude <= 53.6)


def _transform_latitude(x: float, y: float) -> float:
    value = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y
    value += 0.2 * math.sqrt(abs(x))
    value += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    value += (20.0 * math.sin(y * _PI) + 40.0 * math.sin(y / 3.0 * _PI)) * 2.0 / 3.0
    value += (160.0 * math.sin(y / 12.0 * _PI) + 320.0 * math.sin(y * _PI / 30.0)) * 2.0 / 3.0
    return value


def _transform_longitude(x: float, y: float) -> float:
    value = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y
    value += 0.1 * math.sqrt(abs(x))
    value += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    value += (20.0 * math.sin(x * _PI) + 40.0 * math.sin(x / 3.0 * _PI)) * 2.0 / 3.0
    value += (150.0 * math.sin(x / 12.0 * _PI) + 300.0 * math.sin(x / 30.0 * _PI)) * 2.0 / 3.0
    return value


def _wgs84_to_gcj02(longitude: float, latitude: float) -> tuple[float, float]:
    if _outside_china(longitude, latitude):
        return longitude, latitude
    delta_latitude = _transform_latitude(longitude - 105.0, latitude - 35.0)
    delta_longitude = _transform_longitude(longitude - 105.0, latitude - 35.0)
    radians = latitude / 180.0 * _PI
    magic = 1.0 - _ECCENTRICITY_SQUARED * math.sin(radians) ** 2
    root_magic = math.sqrt(magic)
    delta_latitude = (
        delta_latitude
        * 180.0
        / ((_AXIS * (1.0 - _ECCENTRICITY_SQUARED)) / (magic * root_magic) * _PI)
    )
    delta_longitude = delta_longitude * 180.0 / (_AXIS / root_magic * math.cos(radians) * _PI)
    return longitude + delta_longitude, latitude + delta_latitude


def _gcj02_to_wgs84(longitude: float, latitude: float) -> tuple[float, float]:
    if _outside_china(longitude, latitude):
        return longitude, latitude
    estimate_longitude, estimate_latitude = longitude, latitude
    for _ in range(12):
        shifted_longitude, shifted_latitude = _wgs84_to_gcj02(
            estimate_longitude, estimate_latitude
        )
        error_longitude = shifted_longitude - longitude
        error_latitude = shifted_latitude - latitude
        estimate_longitude -= error_longitude
        estimate_latitude -= error_latitude
        if max(abs(error_longitude), abs(error_latitude)) < 1e-10:
            break
    return estimate_longitude, estimate_latitude


def to_wgs84(
    longitude: float, latitude: float, coordinate_system: CoordinateSystem
) -> tuple[float, float]:
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        raise CoordinateConversionError("coordinate must be finite")
    if coordinate_system is CoordinateSystem.WGS84:
        return longitude, latitude
    if coordinate_system is CoordinateSystem.GCJ02:
        return _gcj02_to_wgs84(longitude, latitude)
    raise CoordinateConversionError("unsupported coordinate system")
