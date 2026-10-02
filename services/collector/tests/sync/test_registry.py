from __future__ import annotations

import pytest

from eye_collector.exceptions import AdapterConfigError, SourcePolicyError
from eye_collector.models import SourceDescriptor
from eye_collector.sync.registry import AdapterRegistry


def test_registry_only_creates_explicitly_registered_fixture_adapter() -> None:
    registry = AdapterRegistry.for_tests(fixture_revision="updated")

    descriptor = registry.descriptor("fixture")

    assert descriptor.source_key == "fixture"
    assert descriptor.source_name == "Fixture Directory"
    assert descriptor.catalog_url == "https://fixture.invalid/directory"


def test_registry_rejects_database_supplied_module_or_unknown_adapter_key() -> None:
    with pytest.raises(AdapterConfigError):
        AdapterRegistry().descriptor("evil.module:Factory")


def test_registry_rejects_descriptor_that_does_not_match_approved_catalog() -> None:
    registry = AdapterRegistry()
    descriptor = SourceDescriptor("fixture", "Other Source", "https://fixture.invalid/other")

    with pytest.raises(SourcePolicyError, match="does not match approved source catalog"):
        registry.verify_catalog_descriptor(
            descriptor,
            {"source_name": "Fixture Directory", "catalog_url": "https://fixture.invalid/directory"},
        )
