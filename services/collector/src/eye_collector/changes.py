from __future__ import annotations

from bisect import insort
from enum import StrEnum
from typing import Any


class ChangeType(StrEnum):
    NEW = "NEW"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"


def classify_snapshot(source_key_exists: bool, exact_snapshot_exists: bool) -> ChangeType:
    if exact_snapshot_exists and not source_key_exists:
        raise ValueError("exact snapshot requires an existing source key")
    if not source_key_exists:
        return ChangeType.NEW
    if exact_snapshot_exists:
        return ChangeType.UNCHANGED
    return ChangeType.CHANGED


def changed_json_paths(
    previous: dict[str, Any], current: dict[str, Any], *, max_paths: int = 100
) -> tuple[tuple[str, ...], bool]:
    """Return sorted, bounded field paths that differ between two JSON objects.

    Objects are compared recursively. Arrays and scalar values are treated as a
    single field, avoiding unstable index-level changes for source exports.
    Only the lexicographically first ``max_paths`` paths are retained.
    """
    if max_paths < 1:
        raise ValueError("max_paths must be positive")

    paths: list[str] = []
    truncated = False

    def add(path: str) -> None:
        nonlocal truncated
        insort(paths, path)
        if len(paths) > max_paths:
            paths.pop()
            truncated = True

    def walk(before: Any, after: Any, prefix: str) -> None:
        if isinstance(before, dict) and isinstance(after, dict):
            for key in sorted(before.keys() | after.keys()):
                child = f"{prefix}.{key}" if prefix else str(key)
                if key not in before or key not in after:
                    add(child)
                else:
                    walk(before[key], after[key], child)
            return
        if before != after and prefix:
            add(prefix)

    walk(previous, current, "")
    return tuple(paths), truncated
