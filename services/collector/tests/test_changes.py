from __future__ import annotations

import pytest

from eye_collector.changes import ChangeType, changed_json_paths, classify_snapshot


@pytest.mark.parametrize(
    ("source_key_exists", "exact_snapshot_exists", "expected"),
    [
        (False, False, ChangeType.NEW),
        (True, True, ChangeType.UNCHANGED),
        (True, False, ChangeType.CHANGED),
    ],
)
def test_classifies_incremental_snapshots(
    source_key_exists: bool, exact_snapshot_exists: bool, expected: ChangeType
) -> None:
    assert classify_snapshot(source_key_exists, exact_snapshot_exists) is expected


def test_rejects_an_exact_snapshot_without_a_previously_seen_key() -> None:
    with pytest.raises(ValueError, match="exact snapshot requires an existing source key"):
        classify_snapshot(False, True)


def test_json_paths_are_stable_recursive_and_treat_lists_as_one_field() -> None:
    previous = {"name": "甲", "nested": {"address": "旧址", "same": 1}, "items": [1, 2]}
    current = {"name": "乙", "nested": {"address": "新址", "same": 1}, "items": [1, 3]}

    assert changed_json_paths(previous, current) == (("items", "name", "nested.address"), False)


def test_json_paths_include_added_and_removed_fields() -> None:
    assert changed_json_paths({"old": 1}, {"new": 1}) == (("new", "old"), False)


def test_json_paths_are_bounded_and_report_truncation() -> None:
    previous = {f"field_{index:03}": 0 for index in range(105)}
    current = {f"field_{index:03}": 1 for index in range(105)}

    paths, truncated = changed_json_paths(previous, current, max_paths=100)

    assert paths == tuple(f"field_{index:03}" for index in range(100))
    assert truncated is True


@pytest.mark.parametrize("max_paths", [0, -1])
def test_json_path_limit_must_be_positive(max_paths: int) -> None:
    with pytest.raises(ValueError, match="max_paths must be positive"):
        changed_json_paths({}, {}, max_paths=max_paths)
