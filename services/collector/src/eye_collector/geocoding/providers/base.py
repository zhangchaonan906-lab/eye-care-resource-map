from __future__ import annotations

from typing import Protocol

from eye_collector.geocoding.models import GeocodeErrorCode, GeocodeResult, ProviderPolicy


class GeocodeProviderError(RuntimeError):
    def __init__(self, code: GeocodeErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class GeocodeProvider(Protocol):
    @property
    def policy(self) -> ProviderPolicy: ...

    def geocode(self, address: str, administrative_code: str | None) -> GeocodeResult: ...
