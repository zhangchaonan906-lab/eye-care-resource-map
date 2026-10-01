from __future__ import annotations

import pytest

from eye_collector.geocoding.coordinates import CoordinateConversionError, to_wgs84
from eye_collector.geocoding.models import CoordinateSystem


def test_wgs84_coordinate_is_preserved() -> None:
    assert to_wgs84(116.397, 39.908, CoordinateSystem.WGS84) == (116.397, 39.908)


def test_gcj02_is_converted_and_never_mislabeled_as_wgs84() -> None:
    gcj = (116.403963, 39.915119)

    wgs = to_wgs84(*gcj, CoordinateSystem.GCJ02)

    assert wgs[0] == pytest.approx(116.397719, abs=0.000002)
    assert wgs[1] == pytest.approx(39.913715, abs=0.000002)
    assert wgs != gcj


def test_unknown_coordinate_system_cannot_be_stored_as_wgs84() -> None:
    with pytest.raises(CoordinateConversionError, match="unsupported"):
        to_wgs84(116.4, 39.9, CoordinateSystem.UNKNOWN)
