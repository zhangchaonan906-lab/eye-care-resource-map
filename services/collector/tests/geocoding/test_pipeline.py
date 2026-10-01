from __future__ import annotations

from dataclasses import dataclass

from eye_collector.geocoding.models import (
    CoordinateSystem,
    GeocodeCandidate,
    GeocodeResult,
    GeocodeStatus,
    PrecisionLevel,
    ProviderPolicy,
)
from eye_collector.geocoding.pipeline import GeocodingPipeline
from eye_collector.hashing import canonical_sha256


class Provider:
    policy = ProviderPolicy("fixture", "fixture-v1", True, 10)

    def __init__(self, result: GeocodeResult) -> None:
        self.result = result
        self.requests: list[tuple[str, str | None]] = []

    def geocode(self, address: str, administrative_code: str | None) -> GeocodeResult:
        self.requests.append((address, administrative_code))
        return self.result


@dataclass
class Repository:
    candidates: list[GeocodeCandidate]
    storage_allowed: bool = True
    ignore_limit: bool = False

    def __post_init__(self) -> None:
        self.saved: list[tuple[object, ...]] = []

    def fetch_pending(
        self,
        policy: ProviderPolicy,
        limit: int | None = None,
        candidate_record_id: str | None = None,
    ) -> list[GeocodeCandidate]:
        if candidate_record_id is not None:
            return [
                item
                for item in self.candidates
                if item.candidate_record_id == candidate_record_id
            ]
        if self.ignore_limit or limit is None:
            return self.candidates
        return self.candidates[:limit]

    def count_processed(self, policy: ProviderPolicy) -> int:
        return 0

    def persistent_storage_allowed(self, policy: ProviderPolicy) -> bool:
        return self.storage_allowed

    def region_parents(self, codes: set[str]) -> dict[str, str | None]:
        return {"110000": None, "110100": "110000", "110105": "110100"}

    def persist(self, *values: object) -> bool:
        self.saved.append(values)
        return True


def candidate(address: str = "Fixture address") -> GeocodeCandidate:
    return GeocodeCandidate("candidate-1", "source-1", address, address, "110105")


def result() -> GeocodeResult:
    return GeocodeResult(
        "fixture:1",
        116.397,
        39.908,
        CoordinateSystem.WGS84,
        PrecisionLevel.ROOFTOP,
        "rooftop",
        "Fixture address",
        "110105",
        20,
        GeocodeStatus.SUCCESS,
    )


def test_geocoding_pipeline_persists_validated_wgs84_result() -> None:
    provider = Provider(result())
    repository = Repository([candidate()])

    stats = GeocodingPipeline(repository, provider).run()

    assert stats.candidates_read == 1
    assert stats.geocode_requested == 1
    assert stats.verified == 1
    assert stats.coordinates_created == 1
    assert len(repository.saved) == 1
    saved = repository.saved[0]
    assert saved[1] == candidate()
    assert saved[3].longitude_wgs84 == 116.397
    assert saved[3].latitude_wgs84 == 39.908
    assert saved[4] != saved[5]
    assert saved[4] == canonical_sha256(
        {
            "normalized_address": "Fixture address",
            "administrative_code": "110105",
            "provider": "fixture",
            "provider_version": "fixture-v1",
        }
    )


def test_dry_run_validates_without_persisting() -> None:
    repository = Repository([candidate()])

    stats = GeocodingPipeline(repository, Provider(result())).run(dry_run=True)

    assert stats.verified == 1
    assert stats.coordinates_created == 0
    assert repository.saved == []


def test_policy_denial_discards_all_provider_response_fields() -> None:
    repository = Repository([candidate()], storage_allowed=False)
    provider = Provider(result())

    stats = GeocodingPipeline(repository, provider).run()

    assert stats.needs_review == 1
    saved = repository.saved[0]
    sanitized = saved[2]
    assert isinstance(sanitized, GeocodeResult)
    assert sanitized.provider_record_id is None
    assert sanitized.returned_address is None
    assert sanitized.returned_adcode is None
    assert sanitized.longitude is None
    assert sanitized.latitude is None
    assert sanitized.source_metadata == {}
    assert provider.requests == []


def test_missing_address_is_recorded_as_no_result_without_provider_call() -> None:
    provider = Provider(result())
    repository = Repository([candidate("")])

    stats = GeocodingPipeline(repository, provider).run()

    assert stats.no_result == 1
    assert provider.requests == []
    assert len(repository.saved) == 1


def test_pipeline_enforces_policy_quota_even_if_repository_ignores_limit() -> None:
    policy = ProviderPolicy("fixture", "fixture-v1", True, 10)
    provider = Provider(result())
    provider.policy = policy
    candidates = [candidate(f"address-{index}") for index in range(100)]
    repository = Repository(candidates, ignore_limit=True)

    stats = GeocodingPipeline(repository, provider).run(limit=100)

    assert stats.candidates_read == 10
    assert stats.geocode_requested == 10
    assert len(provider.requests) == 10


def test_pipeline_enforces_provider_rate_limit_independently() -> None:
    policy = ProviderPolicy("fixture", "fixture-v1", True, 10, requests_per_second=2)
    provider = Provider(result())
    provider.policy = policy
    now = [0.0]
    sleeps: list[float] = []

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    repository = Repository([candidate(), candidate("2")])
    pipeline = GeocodingPipeline(
        provider=provider, repository=repository, clock=clock, sleeper=sleep
    )

    pipeline.run()

    assert sleeps == [0.5]
