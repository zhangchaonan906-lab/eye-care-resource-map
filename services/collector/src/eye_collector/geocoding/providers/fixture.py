from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.parse import urlencode

import httpx

from eye_collector.exceptions import HttpRequestError
from eye_collector.geocoding.models import (
    CoordinateSystem,
    GeocodeErrorCode,
    GeocodeResult,
    GeocodeStatus,
    PrecisionLevel,
    ProviderPolicy,
)
from eye_collector.geocoding.providers.base import GeocodeProvider, GeocodeProviderError
from eye_collector.http import HttpClient

_FIXTURE_ENDPOINT = "https://fixture.invalid/geocode"


class FixtureGeocodeTransport(httpx.BaseTransport):
    """Returns deterministic synthetic geocoder responses without network access."""

    _SCENARIOS = {"normal", "retry_429", "timeout", "always_429"}

    def __init__(self, *, scenario: str = "normal") -> None:
        if scenario not in self._SCENARIOS:
            raise ValueError("unsupported geocode fixture scenario")
        self._scenario = scenario
        self.requests: list[tuple[str, str | None]] = []
        self.attempt_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.scheme != "https" or request.url.host != "fixture.invalid":
            raise RuntimeError("fixture geocoder transport only serves fixture.invalid")
        if request.url.path != "/geocode":
            return httpx.Response(404, request=request)

        address = request.url.params.get("address", "")
        administrative_code = request.url.params.get("administrative_code")
        self.requests.append((address, administrative_code))
        self.attempt_count += 1
        if self._scenario == "always_429" or (
            self._scenario == "retry_429" and self.attempt_count == 1
        ):
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        if self._scenario == "timeout" and self.attempt_count == 1:
            raise httpx.ReadTimeout("synthetic geocoder timeout", request=request)

        payload = self._payload(address, administrative_code)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            request=request,
        )

    @staticmethod
    def _payload(address: str, administrative_code: str | None) -> dict[str, object]:
        common: dict[str, object] = {
            "status": "success",
            "provider_record_id": f"fixture:{address}",
            "longitude": 116.397,
            "latitude": 39.908,
            "coordinate_system": "WGS84",
            "precision_level": "rooftop",
            "result_type": "rooftop",
            "returned_address": address,
            "returned_adcode": administrative_code,
            "accuracy_m": 20,
        }
        if address == "Fixture GCJ":
            common.update(
                longitude=116.403963,
                latitude=39.915119,
                coordinate_system="GCJ02",
                precision_level="building",
                result_type="building",
                accuracy_m=30,
            )
        elif address == "Fixture Parent Region":
            common["returned_adcode"] = "110100"
        elif address == "Fixture Mismatch":
            common["returned_adcode"] = "310101"
        elif address == "Fixture City":
            common["precision_level"] = "city"
            common["result_type"] = "city"
            common["accuracy_m"] = 10_000
        elif address == "Fixture Invalid Longitude":
            common["longitude"] = 181.0
        elif address == "Fixture Invalid Latitude":
            common["latitude"] = 91.0
        elif address == "Fixture Null Island":
            common["longitude"] = 0.0
            common["latitude"] = 0.0
        elif address in {"", "Fixture No Result"}:
            return {
                "status": "no_result",
                "provider_record_id": None,
                "coordinate_system": "UNKNOWN",
                "precision_level": "unknown",
                "result_type": "none",
                "returned_address": None,
                "returned_adcode": None,
                "accuracy_m": None,
            }
        elif address == "Fixture Ambiguous":
            return {
                "status": "ambiguous",
                "provider_record_id": None,
                "coordinate_system": "UNKNOWN",
                "precision_level": "unknown",
                "result_type": "multiple",
                "returned_address": None,
                "returned_adcode": None,
                "accuracy_m": None,
            }
        return common


class FixtureGeocoder(GeocodeProvider):
    def __init__(
        self,
        client: HttpClient,
        *,
        policy: ProviderPolicy | None = None,
        quota_per_run: int = 1_000,
        requests_per_second: float = 5.0,
    ) -> None:
        self._client = client
        self._policy = policy or ProviderPolicy(
            provider="fixture",
            version="fixture-v1",
            persistent_storage_allowed=True,
            quota_per_run=quota_per_run,
            requests_per_second=requests_per_second,
        )
        if self._policy.provider != "fixture" or self._policy.version != "fixture-v1":
            raise ValueError("fixture geocoder requires the fixture-v1 provider policy")
        self._requests = 0

    @property
    def policy(self) -> ProviderPolicy:
        return self._policy

    def close(self) -> None:
        self._client.close()

    def geocode(self, address: str, administrative_code: str | None) -> GeocodeResult:
        if not address.strip():
            return self._semantic_result(GeocodeStatus.NO_RESULT, GeocodeErrorCode.NO_RESULT)
        if self._requests >= self._policy.quota_per_run:
            raise GeocodeProviderError(GeocodeErrorCode.RATE_LIMITED, "provider run quota reached")
        self._requests += 1
        query: dict[str, str] = {"address": address}
        if administrative_code is not None:
            query["administrative_code"] = administrative_code
        try:
            response = self._client.get(
                f"{_FIXTURE_ENDPOINT}?{urlencode(query)}",
                source_key=self._policy.provider,
                requests_per_second=self._policy.requests_per_second,
                min_delay_ms=0,
            )
        except HttpRequestError as error:
            code = (
                GeocodeErrorCode.RATE_LIMITED
                if "HTTP 429" in str(error)
                else GeocodeErrorCode.PROVIDER_ERROR
            )
            raise GeocodeProviderError(code, "fixture geocoder request failed") from error

        try:
            payload = json.loads(response.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GeocodeProviderError(
                GeocodeErrorCode.PROVIDER_ERROR, "provider returned malformed JSON"
            ) from error
        return self._parse_result(payload)

    @staticmethod
    def _semantic_result(status: GeocodeStatus, code: GeocodeErrorCode) -> GeocodeResult:
        return GeocodeResult(
            provider_record_id=None,
            longitude=None,
            latitude=None,
            original_coordinate_system=CoordinateSystem.UNKNOWN,
            precision_level=PrecisionLevel.UNKNOWN,
            result_type="none",
            returned_address=None,
            returned_adcode=None,
            accuracy_m=None,
            status=status,
            error_code=code,
        )

    @classmethod
    def _parse_result(cls, payload: object) -> GeocodeResult:
        if not isinstance(payload, Mapping):
            raise GeocodeProviderError(
                GeocodeErrorCode.PROVIDER_ERROR, "provider response must be an object"
            )
        try:
            status = GeocodeStatus(str(payload["status"]))
            system = CoordinateSystem(str(payload["coordinate_system"]))
            precision = PrecisionLevel(str(payload["precision_level"]))
        except (KeyError, ValueError) as error:
            raise GeocodeProviderError(
                GeocodeErrorCode.PROVIDER_ERROR, "provider response has invalid status metadata"
            ) from error

        if status is GeocodeStatus.NO_RESULT:
            return cls._semantic_result(status, GeocodeErrorCode.NO_RESULT)
        if status is GeocodeStatus.AMBIGUOUS:
            return cls._semantic_result(status, GeocodeErrorCode.AMBIGUOUS_RESULT)

        longitude = payload.get("longitude")
        latitude = payload.get("latitude")
        accuracy = payload.get("accuracy_m")
        if (
            not isinstance(longitude, (int, float))
            or isinstance(longitude, bool)
            or not isinstance(latitude, (int, float))
            or isinstance(latitude, bool)
            or (
                accuracy is not None
                and (not isinstance(accuracy, int) or isinstance(accuracy, bool))
            )
        ):
            raise GeocodeProviderError(
                GeocodeErrorCode.PROVIDER_ERROR, "provider response has malformed coordinates"
            )
        provider_record_id = payload.get("provider_record_id")
        returned_address = payload.get("returned_address")
        returned_adcode = payload.get("returned_adcode")
        result_type = payload.get("result_type")
        if not isinstance(result_type, str):
            raise GeocodeProviderError(
                GeocodeErrorCode.PROVIDER_ERROR, "provider response is missing result type"
            )
        return GeocodeResult(
            provider_record_id=(
                provider_record_id if isinstance(provider_record_id, str) else None
            ),
            longitude=float(longitude),
            latitude=float(latitude),
            original_coordinate_system=system,
            precision_level=precision,
            result_type=result_type,
            returned_address=(returned_address if isinstance(returned_address, str) else None),
            returned_adcode=(returned_adcode if isinstance(returned_adcode, str) else None),
            accuracy_m=accuracy,
            status=status,
            source_metadata={"fixture": True},
        )
