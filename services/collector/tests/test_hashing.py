from __future__ import annotations

import hashlib

import pytest

from eye_collector.hashing import canonical_sha256


def test_canonical_hash_ignores_mapping_key_order() -> None:
    first = {"name": "测试医院", "details": {"phone": "010-12345678", "city": "北京"}}
    second = {"details": {"city": "北京", "phone": "010-12345678"}, "name": "测试医院"}

    assert canonical_sha256(first) == canonical_sha256(second)


def test_canonical_hash_changes_when_content_changes() -> None:
    assert canonical_sha256({"name": "旧名称"}) != canonical_sha256({"name": "新名称"})


def test_canonical_hash_matches_sha256_of_canonical_utf8_json() -> None:
    payload = {"name": "眼科"}
    canonical = '{"name":"眼科"}'.encode()

    assert canonical_sha256(payload) == hashlib.sha256(canonical).hexdigest()


def test_canonical_hash_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="canonical JSON"):
        canonical_sha256({"value": float("nan")})
