from __future__ import annotations

from typing import Any

from eye_collector.exceptions import AdapterConfigError, SourcePolicyError
from eye_collector.http import HttpClient
from eye_collector.models import SourceDescriptor
from eye_collector.sources.fixture import FixtureSourceAdapter


class AdapterRegistry:
    """An allowlist of source adapters compiled into the worker."""

    def __init__(self, *, fixture_revision: str = "stable", test_only: bool = False) -> None:
        if fixture_revision not in {"stable", "updated"}:
            raise ValueError("fixture revision must be stable or updated")
        if fixture_revision != "stable" and not test_only:
            raise ValueError("non-stable fixture revisions are test-only")
        self._fixture_revision = fixture_revision

    @property
    def fixture_revision(self) -> str:
        """Return the allowlisted fixture revision used by this registry."""
        return self._fixture_revision

    @classmethod
    def for_tests(cls, *, fixture_revision: str = "stable") -> AdapterRegistry:
        return cls(fixture_revision=fixture_revision, test_only=True)

    def descriptor(self, adapter_key: str) -> SourceDescriptor:
        if adapter_key != "fixture":
            raise AdapterConfigError("adapter key is not registered")
        return SourceDescriptor(
            source_key="fixture",
            source_name="Fixture Directory",
            catalog_url="https://fixture.invalid/directory",
        )

    def create(self, adapter_key: str, http: HttpClient) -> FixtureSourceAdapter:
        self.descriptor(adapter_key)
        return FixtureSourceAdapter(http, revision=self._fixture_revision)

    @staticmethod
    def verify_catalog_descriptor(
        descriptor: SourceDescriptor, catalog: dict[str, Any]
    ) -> None:
        if (
            catalog.get("source_name") != descriptor.source_name
            or catalog.get("catalog_url") != descriptor.catalog_url
        ):
            raise SourcePolicyError("adapter descriptor does not match approved source catalog")
