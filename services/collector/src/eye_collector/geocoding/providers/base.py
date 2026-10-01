from __future__ import annotations

from typing import Protocol

from eye_collector.geocoding.models import GeocodeResult, ProviderPolicy


class GeocodeProvider(Protocol):
    @property
    def policy(self) -> ProviderPolicy: ...

    def geocode(self, address: str, administrative_code: str | None) -> GeocodeResult: ...
