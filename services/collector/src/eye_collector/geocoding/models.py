from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CoordinateSystem(StrEnum):
    WGS84 = "WGS84"
    GCJ02 = "GCJ02"
    UNKNOWN = "UNKNOWN"


class PrecisionLevel(StrEnum):
    ROOFTOP = "rooftop"
    BUILDING = "building"
    STREET = "street"
    DISTRICT = "district"
    CITY = "city"
    UNKNOWN = "unknown"


class GeocodeErrorCode(StrEnum):
    NO_RESULT = "NO_RESULT"
    AMBIGUOUS_RESULT = "AMBIGUOUS_RESULT"
    REGION_MISMATCH = "REGION_MISMATCH"
    LOW_PRECISION = "LOW_PRECISION"
    INVALID_COORDINATE = "INVALID_COORDINATE"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    POLICY_BLOCKED = "POLICY_BLOCKED"


class GeocodeStatus(StrEnum):
    SUCCESS = "success"
    NO_RESULT = "no_result"
    AMBIGUOUS = "ambiguous"


class ValidationStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    provider: str
    version: str
    persistent_storage_allowed: bool
    quota_per_run: int
    requests_per_second: float = 1.0

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.version.strip():
            raise ValueError("provider and version are required")
        if self.quota_per_run < 0:
            raise ValueError("provider quota must be non-negative")
        if self.requests_per_second <= 0:
            raise ValueError("provider rate limit must be positive")


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    provider_record_id: str | None
    longitude: float | None
    latitude: float | None
    original_coordinate_system: CoordinateSystem
    precision_level: PrecisionLevel
    result_type: str
    returned_address: str | None
    returned_adcode: str | None
    accuracy_m: int | None
    status: GeocodeStatus = GeocodeStatus.SUCCESS
    error_code: GeocodeErrorCode | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CoordinateValidation:
    status: ValidationStatus
    error_code: GeocodeErrorCode | None
    reason: str | None
    longitude_wgs84: float | None
    latitude_wgs84: float | None


@dataclass(frozen=True, slots=True)
class GeocodeCandidate:
    candidate_record_id: str
    source_record_id: str
    address: str | None
    normalized_address: str | None
    administrative_code: str | None


@dataclass(frozen=True, slots=True)
class GeocodeStats:
    candidates_read: int = 0
    geocode_requested: int = 0
    coordinates_created: int = 0
    already_processed: int = 0
    verified: int = 0
    needs_review: int = 0
    rejected: int = 0
    no_result: int = 0
    region_mismatch: int = 0
    low_precision: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "candidates_read": self.candidates_read,
            "geocode_requested": self.geocode_requested,
            "coordinates_created": self.coordinates_created,
            "already_processed": self.already_processed,
            "verified": self.verified,
            "needs_review": self.needs_review,
            "rejected": self.rejected,
            "no_result": self.no_result,
            "region_mismatch": self.region_mismatch,
            "low_precision": self.low_precision,
            "errors": self.errors,
        }
