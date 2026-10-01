from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from eye_collector.geocoding.models import (
    CoordinateSystem,
    CoordinateValidation,
    GeocodeCandidate,
    GeocodeErrorCode,
    GeocodeResult,
    GeocodeStats,
    GeocodeStatus,
    PrecisionLevel,
    ProviderPolicy,
    ValidationStatus,
)
from eye_collector.geocoding.providers.base import GeocodeProvider, GeocodeProviderError
from eye_collector.geocoding.validation import validate_result
from eye_collector.hashing import canonical_sha256


class GeocodingRepository(Protocol):
    def fetch_pending(
        self,
        policy: ProviderPolicy,
        limit: int | None = None,
        candidate_record_id: str | None = None,
    ) -> list[GeocodeCandidate]: ...

    def count_processed(self, policy: ProviderPolicy) -> int: ...

    def persistent_storage_allowed(self, policy: ProviderPolicy) -> bool: ...

    def region_parents(self, codes: set[str]) -> dict[str, str | None]: ...

    def persist(
        self,
        policy: ProviderPolicy,
        candidate: GeocodeCandidate,
        result: GeocodeResult,
        validation: CoordinateValidation,
        address_fingerprint: str,
        result_fingerprint: str,
        request_at: datetime,
        retrieval_at: datetime,
    ) -> bool: ...


def _result_payload(result: GeocodeResult) -> dict[str, object]:
    return {
        "provider_record_id": result.provider_record_id,
        "longitude": result.longitude,
        "latitude": result.latitude,
        "coordinate_system": result.original_coordinate_system.value,
        "precision_level": result.precision_level.value,
        "result_type": result.result_type,
        "returned_address": result.returned_address,
        "returned_adcode": result.returned_adcode,
        "accuracy_m": result.accuracy_m,
        "status": result.status.value,
        "error_code": result.error_code.value if result.error_code else None,
        "source_metadata": result.source_metadata,
    }


def _policy_blocked_result() -> GeocodeResult:
    return GeocodeResult(
        provider_record_id=None,
        longitude=None,
        latitude=None,
        original_coordinate_system=CoordinateSystem.UNKNOWN,
        precision_level=PrecisionLevel.UNKNOWN,
        result_type="policy_blocked",
        returned_address=None,
        returned_adcode=None,
        accuracy_m=None,
        status=GeocodeStatus.NO_RESULT,
        error_code=GeocodeErrorCode.POLICY_BLOCKED,
        source_metadata={},
    )


class GeocodingPipeline:
    def __init__(
        self,
        repository: GeocodingRepository,
        provider: GeocodeProvider,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._logger = logger or logging.getLogger("eye_collector.geocoding")

    def run(
        self,
        *,
        limit: int | None = None,
        candidate_record_id: str | None = None,
        dry_run: bool = False,
    ) -> GeocodeStats:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive integer")
        policy = self._provider.policy
        candidates = self._repository.fetch_pending(policy, limit, candidate_record_id)
        counts = {key: 0 for key in GeocodeStats().as_dict()}
        counts["candidates_read"] = len(candidates)
        counts["already_processed"] = self._repository.count_processed(policy)
        parents = self._repository.region_parents(
            {
                candidate.administrative_code
                for candidate in candidates
                if candidate.administrative_code
            }
        )
        storage_allowed = self._repository.persistent_storage_allowed(policy)

        for candidate in candidates:
            request_at = datetime.now(UTC)
            address = candidate.address or ""
            address_fingerprint = canonical_sha256(
                {
                    "normalized_address": candidate.normalized_address or "",
                    "administrative_code": candidate.administrative_code,
                    "provider": policy.provider,
                    "provider_version": policy.version,
                }
            )
            try:
                if not storage_allowed:
                    result = _policy_blocked_result()
                    validation = CoordinateValidation(
                        ValidationStatus.NEEDS_REVIEW,
                        GeocodeErrorCode.POLICY_BLOCKED,
                        "provider_response_persistence_not_allowed",
                        None,
                        None,
                    )
                elif address.strip():
                    counts["geocode_requested"] += 1
                    result = self._provider.geocode(address, candidate.administrative_code)
                    if result.accuracy_m is not None and result.accuracy_m < 0:
                        result = replace(result, accuracy_m=None)
                    validation = validate_result(
                        result, candidate.administrative_code, parents
                    )
                else:
                    result = GeocodeResult(
                        provider_record_id=None,
                        longitude=None,
                        latitude=None,
                        original_coordinate_system=CoordinateSystem.UNKNOWN,
                        precision_level=PrecisionLevel.UNKNOWN,
                        result_type="none",
                        returned_address=None,
                        returned_adcode=None,
                        accuracy_m=None,
                        status=GeocodeStatus.NO_RESULT,
                        error_code=GeocodeErrorCode.NO_RESULT,
                    )
                    validation = validate_result(
                        result, candidate.administrative_code, parents
                    )
                retrieval_at = datetime.now(UTC)
                result_fingerprint = canonical_sha256(_result_payload(result))
                inserted = False
                if not dry_run:
                    inserted = self._repository.persist(
                        policy,
                        candidate,
                        result,
                        validation,
                        address_fingerprint,
                        result_fingerprint,
                        request_at,
                        retrieval_at,
                    )
                if inserted:
                    counts["coordinates_created"] += 1
                self._count_outcome(counts, result, validation)
            except GeocodeProviderError as error:
                counts["errors"] += 1
                self._logger.warning(
                    "geocode_provider_failed",
                    extra={
                        "event": "geocode_provider_failed",
                        "candidate_record_id": candidate.candidate_record_id,
                        "error_code": error.code.value,
                    },
                )
            except Exception as error:
                counts["errors"] += 1
                self._logger.warning(
                    "geocode_candidate_failed",
                    extra={
                        "event": "geocode_candidate_failed",
                        "candidate_record_id": candidate.candidate_record_id,
                        "error_type": type(error).__name__,
                    },
                )

        stats = GeocodeStats(**counts)
        self._logger.info(
            "geocoding_completed", extra={"event": "geocoding_completed", **stats.as_dict()}
        )
        return stats

    @staticmethod
    def _count_outcome(
        counts: dict[str, int], result: GeocodeResult, validation: CoordinateValidation
    ) -> None:
        if validation.status is ValidationStatus.VERIFIED:
            counts["verified"] += 1
        elif validation.status is ValidationStatus.NEEDS_REVIEW:
            counts["needs_review"] += 1
        else:
            counts["rejected"] += 1
        if (
            result.status is GeocodeStatus.NO_RESULT
            or validation.error_code is GeocodeErrorCode.NO_RESULT
        ):
            counts["no_result"] += 1
        if validation.error_code is GeocodeErrorCode.REGION_MISMATCH:
            counts["region_mismatch"] += 1
        if validation.error_code is GeocodeErrorCode.LOW_PRECISION:
            counts["low_precision"] += 1
