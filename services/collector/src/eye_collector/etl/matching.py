from __future__ import annotations

import unicodedata

from eye_collector.etl.models import FacilityTarget, MatchResult, NormalizedRecord
from eye_collector.etl.normalization import normalize_text


def _identifier(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(unicodedata.normalize("NFKC", value).split()).casefold() or None


def _campus_matches(candidate_campus: str | None, facility_campus: str | None) -> bool:
    return normalize_text(candidate_campus) == normalize_text(facility_campus)


def _result_for_targets(
    targets: list[FacilityTarget], *, matched_reason: str, review_reason: str
) -> MatchResult:
    if len(targets) == 1:
        return MatchResult("matched", targets[0].facility_id, matched_reason)
    if targets:
        return MatchResult("needs_review", None, review_reason)
    return MatchResult("unmatched", None, "no_deterministic_match")


def match_facility(
    candidate: NormalizedRecord, facilities: list[FacilityTarget]
) -> MatchResult:
    if candidate.registration_id_reliable and candidate.registration_id:
        registration = _identifier(candidate.registration_id)
        registration_matches = [
            facility
            for facility in facilities
            if _identifier(facility.registration_id) == registration
        ]
        if registration_matches:
            if candidate.campus_name is not None:
                campus_matches = [
                    facility
                    for facility in registration_matches
                    if _campus_matches(candidate.campus_name, facility.campus_name)
                ]
                if campus_matches:
                    return _result_for_targets(
                        campus_matches,
                        matched_reason="reliable_registration_id_and_campus_exact",
                        review_reason="registration_and_campus_ambiguous",
                    )
                return MatchResult("needs_review", None, "registration_campus_conflict")
            return _result_for_targets(
                registration_matches,
                matched_reason="reliable_registration_id_exact",
                review_reason="registration_id_ambiguous",
            )

    if candidate.administrative_code is None or not candidate.normalized_name:
        return MatchResult("unmatched", None, "missing_name_or_administrative_code")

    same_name_region = [
        facility
        for facility in facilities
        if normalize_text(facility.name) == candidate.normalized_name
        and facility.administrative_code == candidate.administrative_code
    ]
    if not same_name_region:
        return MatchResult("unmatched", None, "no_deterministic_match")

    if candidate.campus_name is not None:
        campus_matches = [
            facility
            for facility in same_name_region
            if _campus_matches(candidate.campus_name, facility.campus_name)
        ]
        if not campus_matches:
            return MatchResult("needs_review", None, "campus_conflict")
        return _result_for_targets(
            campus_matches,
            matched_reason="normalized_name_region_and_campus_exact",
            review_reason="campus_ambiguous",
        )

    campusless = [facility for facility in same_name_region if facility.campus_name is None]
    if campusless:
        return _result_for_targets(
            campusless,
            matched_reason="normalized_name_and_region_exact",
            review_reason="name_region_ambiguous",
        )
    return MatchResult("needs_review", None, "campus_ambiguous")


def duplicate_key(candidate: NormalizedRecord) -> tuple[str, ...] | None:
    campus = normalize_text(candidate.campus_name) or ""
    if candidate.registration_id_reliable and candidate.registration_id:
        registration = _identifier(candidate.registration_id)
        if registration:
            return "registration_id", registration, campus
    if candidate.administrative_code and candidate.normalized_name:
        return (
            "name_region_campus",
            candidate.normalized_name,
            candidate.administrative_code,
            campus,
        )
    return None
