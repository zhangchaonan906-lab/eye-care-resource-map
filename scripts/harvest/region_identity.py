"""Resolve province identity from a region label and an administrative code.

This small harvest utility is intentionally conservative: the code is required,
and a recognized province-level alias in the label must agree with that code.
"""

from __future__ import annotations


_PROVINCE_BY_PREFIX = {
    "11": "北京",
    "12": "天津",
    "13": "河北",
    "14": "山西",
    "15": "内蒙古",
    "21": "辽宁",
    "22": "吉林",
    "23": "黑龙江",
    "31": "上海",
    "32": "江苏",
    "33": "浙江",
    "34": "安徽",
    "35": "福建",
    "36": "江西",
    "37": "山东",
    "41": "河南",
    "42": "湖北",
    "43": "湖南",
    "44": "广东",
    "45": "广西",
    "46": "海南",
    "50": "重庆",
    "51": "四川",
    "52": "贵州",
    "53": "云南",
    "54": "西藏",
    "61": "陕西",
    "62": "甘肃",
    "63": "青海",
    "64": "宁夏",
    "65": "新疆",
    "71": "台湾",
    "81": "香港",
    "82": "澳门",
}

_REGION_ALIASES = {
    "北京市": "北京",
    "天津市": "天津",
    "内蒙古自治区": "内蒙古",
    "广西壮族自治区": "广西",
    "海南州": "青海",
    "海南藏族自治州": "青海",
    "重庆市": "重庆",
    "西藏自治区": "西藏",
    "宁夏回族自治区": "宁夏",
    "新疆维吾尔自治区": "新疆",
    "香港特别行政区": "香港",
    "澳门特别行政区": "澳门",
}


class RegionIdentityError(ValueError):
    """Raised when a region label and its administrative code are unsafe."""


def resolve_province(region_label: str, administrative_code: str | None) -> str:
    """Return a province name, rejecting missing or conflicting identity data."""
    label = region_label.strip()
    code = (administrative_code or "").strip()
    if not code:
        raise RegionIdentityError("administrative code is required")
    if len(code) != 6 or not code.isdigit():
        raise RegionIdentityError("administrative code must contain six digits")

    province = _PROVINCE_BY_PREFIX.get(code[:2])
    if province is None:
        raise RegionIdentityError(f"unknown administrative code prefix: {code[:2]}")

    label_province = _REGION_ALIASES.get(label)
    if label_province is None:
        label_province = next(
            (name for name in set(_PROVINCE_BY_PREFIX.values()) if label == name or label == f"{name}省"),
            None,
        )
    if label_province is not None and label_province != province:
        raise RegionIdentityError(
            f"region label {label!r} conflicts with administrative code for {province}"
        )
    return province
