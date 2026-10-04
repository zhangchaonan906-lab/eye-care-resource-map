"""Verify local Harvest Store files against its metadata-only manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _issue(source_key: str | None, code: str, **details: Any) -> dict[str, Any]:
    return {"source_key": source_key, "code": code, **details}


def _safe_path(root: Path, relative_path: str) -> Path | None:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_store(store_root: Path) -> dict[str, Any]:
    """Check all locally acquired dataset files and report historical gaps."""
    root = store_root.resolve()
    manifest_path = root / "manifests" / "master-manifest.json"
    if not manifest_path.is_file():
        return {
            "status": "FAIL",
            "datasets_checked": 0,
            "historical_records": 0,
            "issues": [_issue(None, "MANIFEST_FILE_MISSING")],
        }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "FAIL",
            "datasets_checked": 0,
            "historical_records": 0,
            "issues": [_issue(None, "MANIFEST_INVALID")],
        }
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return {
            "status": "FAIL",
            "datasets_checked": 0,
            "historical_records": 0,
            "issues": [_issue(None, "MANIFEST_INVALID")],
        }

    datasets = manifest.get("datasets")
    historical_records = manifest.get("historical_records", [])
    if not isinstance(datasets, list) or not isinstance(historical_records, list):
        return {
            "status": "FAIL",
            "datasets_checked": 0,
            "historical_records": 0,
            "issues": [_issue(None, "MANIFEST_INVALID")],
        }

    issues: list[dict[str, Any]] = []
    historical_missing = False
    failed = False

    for record in datasets:
        if not isinstance(record, dict):
            issues.append(_issue(None, "DATASET_RECORD_INVALID"))
            failed = True
            continue
        source_key = record.get("source_key")
        relative_dir = record.get("local_relative_path")
        filename = record.get("filename")
        if not all(isinstance(value, str) and value for value in (relative_dir, filename)):
            issues.append(_issue(source_key, "DATASET_RECORD_INVALID"))
            failed = True
            continue

        record_dir = _safe_path(root, relative_dir)
        original = (
            _safe_path(root, str(Path(relative_dir) / "original" / filename))
            if record_dir is not None
            else None
        )
        if record_dir is None or original is None:
            issues.append(_issue(source_key, "PATH_OUTSIDE_STORE"))
            failed = True
            continue

        metadata_name = record.get("metadata_file", "metadata.json")
        inspection_name = record.get("inspection_file", "inspection.json")
        metadata_path = _safe_path(root, str(Path(relative_dir) / metadata_name))
        inspection_path = _safe_path(root, str(Path(relative_dir) / inspection_name))
        record_failed = False

        if not original.is_file():
            issues.append(_issue(source_key, "LOCAL_SOURCE_FILE_MISSING"))
            record_failed = True
        if metadata_path is None or not metadata_path.is_file():
            issues.append(_issue(source_key, "METADATA_FILE_MISSING"))
            record_failed = True
        if inspection_path is None or not inspection_path.is_file():
            issues.append(_issue(source_key, "INSPECTION_FILE_MISSING"))
            record_failed = True
        if original.is_file():
            expected_hash = record.get("sha256")
            if not isinstance(expected_hash, str) or not _SHA256_RE.fullmatch(expected_hash):
                issues.append(_issue(source_key, "MANIFEST_HASH_INVALID"))
                record_failed = True
            elif _sha256(original) != expected_hash:
                issues.append(_issue(source_key, "SHA256_MISMATCH"))
                record_failed = True

            expected_size = record.get("size_bytes")
            if not isinstance(expected_size, int) or isinstance(expected_size, bool):
                issues.append(_issue(source_key, "MANIFEST_SIZE_INVALID"))
                record_failed = True
            elif original.stat().st_size != expected_size:
                issues.append(_issue(source_key, "SIZE_MISMATCH"))
                record_failed = True

        if record_failed:
            failed = True

    for record in historical_records:
        if not isinstance(record, dict):
            issues.append(_issue(None, "HISTORICAL_RECORD_INVALID"))
            failed = True
            continue
        if record.get("historical_record_only") and not record.get("local_file_available"):
            issues.append(
                _issue(
                    record.get("source_key"),
                    "LOCAL_SOURCE_FILE_MISSING",
                    historical_record_only=True,
                )
            )
            historical_missing = True
        elif record.get("local_file_available") and not record.get("hash_verifiable_now"):
            issues.append(_issue(record.get("source_key"), "HISTORICAL_HASH_UNVERIFIABLE"))
            historical_missing = True

    status = "FAIL" if failed else "PARTIAL" if historical_missing else "PASS"
    return {
        "status": status,
        "datasets_checked": len(datasets),
        "historical_records": len(historical_records),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store_root", type=Path, help="Path to the local HarvestStore root")
    args = parser.parse_args(argv)
    result = verify_store(args.store_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"PASS": 0, "PARTIAL": 1, "FAIL": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
