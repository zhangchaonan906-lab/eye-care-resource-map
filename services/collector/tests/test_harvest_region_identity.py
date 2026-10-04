from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "harvest"))

from region_identity import RegionIdentityError, resolve_province  # noqa: E402


def test_hainan_prefecture_alias_resolves_to_qinghai_from_code() -> None:
    assert resolve_province("海南州", "630000") == "青海"


def test_hainan_province_resolves_from_code() -> None:
    assert resolve_province("海南省", "460000") == "海南"


@pytest.mark.parametrize(
    ("label", "code"),
    [("海南州", "460000"), ("海南省", "630000"), ("海南省", None)],
)
def test_conflicting_or_missing_identity_is_rejected(
    label: str, code: str | None
) -> None:
    with pytest.raises(RegionIdentityError):
        resolve_province(label, code)
