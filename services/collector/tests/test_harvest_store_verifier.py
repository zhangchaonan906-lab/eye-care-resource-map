from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "harvest"))

from verify_store import verify_store  # noqa: E402


def _write_valid_store(tmp_path: Path) -> bytes:
    root = tmp_path / "HarvestStore"
    record_dir = root / "sources" / "test-source" / "2026-10-05_ab12cd34"
    original_dir = record_dir / "original"
    original_dir.mkdir(parents=True)
    original = b"official bytes\x00\xff"
    (original_dir / "source.xlsx").write_bytes(original)
    (record_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (record_dir / "inspection.json").write_text("{}", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "datasets": [
            {
                "source_key": "test-source",
                "local_relative_path": "sources/test-source/2026-10-05_ab12cd34",
                "filename": "source.xlsx",
                "sha256": hashlib.sha256(original).hexdigest(),
                "size_bytes": len(original),
                "metadata_file": "metadata.json",
                "inspection_file": "inspection.json",
                "historical_record_only": False,
                "local_file_available": True,
                "hash_verifiable_now": True,
            }
        ],
        "historical_records": [],
    }
    manifests = root / "manifests"
    manifests.mkdir()
    (manifests / "master-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return original


def test_verifies_original_hash_size_and_required_sidecars(tmp_path: Path) -> None:
    _write_valid_store(tmp_path)

    result = verify_store(tmp_path / "HarvestStore")

    assert result["status"] == "PASS"
    assert result["datasets_checked"] == 1
    assert result["issues"] == []


def test_reports_missing_historical_file_as_known_partial_not_reproducible(
    tmp_path: Path,
) -> None:
    root = tmp_path / "HarvestStore"
    manifests = root / "manifests"
    manifests.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "datasets": [],
        "historical_records": [
            {
                "source_key": None,
                "historical_record_only": True,
                "local_file_available": False,
                "hash_verifiable_now": False,
                "dataset_count": 18,
                "row_count": 14734,
            }
        ],
    }
    (manifests / "master-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = verify_store(root)

    assert result["status"] == "PARTIAL"
    assert result["historical_records"] == 1
    assert result["issues"] == [
        {
            "source_key": None,
            "code": "LOCAL_SOURCE_FILE_MISSING",
            "historical_record_only": True,
        }
    ]


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        ("missing_original", "LOCAL_SOURCE_FILE_MISSING"),
        ("wrong_hash", "SHA256_MISMATCH"),
        ("wrong_size", "SIZE_MISMATCH"),
        ("missing_metadata", "METADATA_FILE_MISSING"),
        ("missing_inspection", "INSPECTION_FILE_MISSING"),
        ("path_traversal", "PATH_OUTSIDE_STORE"),
    ],
)
def test_fails_acquired_record_integrity_errors(
    tmp_path: Path, mutate: str, expected_code: str
) -> None:
    _write_valid_store(tmp_path)
    root = tmp_path / "HarvestStore"
    manifest_path = root / "manifests" / "master-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = manifest["datasets"][0]
    record_dir = root / item["local_relative_path"]
    if mutate == "missing_original":
        (record_dir / "original" / item["filename"]).unlink()
    elif mutate == "wrong_hash":
        item["sha256"] = "0" * 64
    elif mutate == "wrong_size":
        item["size_bytes"] += 1
    elif mutate == "missing_metadata":
        (record_dir / item["metadata_file"]).unlink()
    elif mutate == "missing_inspection":
        (record_dir / item["inspection_file"]).unlink()
    elif mutate == "path_traversal":
        item["local_relative_path"] = "../outside"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = verify_store(root)

    assert result["status"] == "FAIL"
    assert expected_code in {issue["code"] for issue in result["issues"]}


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    result = verify_store(tmp_path / "does-not-exist")

    assert result["status"] == "FAIL"
    assert result["issues"] == [{"source_key": None, "code": "MANIFEST_FILE_MISSING"}]
