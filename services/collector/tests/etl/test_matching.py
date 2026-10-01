from __future__ import annotations

from eye_collector.etl.matching import duplicate_key, match_facility
from eye_collector.etl.models import FacilityTarget, NormalizedRecord


def record(**overrides: object) -> NormalizedRecord:
    values: dict[str, object] = {
        "source_record_id": "source-1",
        "original_name": "示例医院",
        "normalized_name": "示例医院",
        "original_address": None,
        "normalized_address": None,
        "original_phone": None,
        "normalized_phone": None,
        "administrative_code": "110105",
        "registration_id": None,
        "registration_id_reliable": False,
        "campus_name": None,
        "raw_payload": {},
    }
    values.update(overrides)
    return NormalizedRecord(**values)  # type: ignore[arg-type]


def target(
    facility_id: str = "facility-1",
    *,
    name: str = "示例医院",
    administrative_code: str = "110105",
    campus_name: str | None = None,
    registration_id: str | None = None,
) -> FacilityTarget:
    return FacilityTarget(
        facility_id=facility_id,
        name=name,
        campus_name=campus_name,
        administrative_code=administrative_code,
        registration_id=registration_id,
    )


def test_reliable_registration_id_exact_match_has_priority() -> None:
    candidate = record(
        registration_id="REG-9",
        registration_id_reliable=True,
        normalized_name="Other Name",
        administrative_code="310101",
    )

    result = match_facility(candidate, [target(registration_id="REG-9")])

    assert (result.status, result.facility_id, result.reason) == (
        "matched",
        "facility-1",
        "reliable_registration_id_exact",
    )


def test_untrusted_registration_id_does_not_match_by_registration_id() -> None:
    candidate = record(registration_id="REG-9", registration_id_reliable=False)

    result = match_facility(
        candidate, [target(name="Completely Different", registration_id="REG-9")]
    )

    assert result.status == "unmatched"


def test_name_match_requires_exact_name_and_explicit_administrative_code() -> None:
    assert match_facility(record(), [target()]).facility_id == "facility-1"
    assert match_facility(record(administrative_code=None), [target()]).status == "unmatched"
    assert match_facility(record(), [target(administrative_code="110106")]).status == "unmatched"
    assert match_facility(record(), [target(name="示例医院分院")]).status == "unmatched"


def test_explicit_campus_must_match_exactly() -> None:
    candidate = record(campus_name="东院")

    exact = match_facility(candidate, [target(campus_name="东院")])
    uncertain = match_facility(candidate, [target(campus_name="西院")])

    assert exact.facility_id == "facility-1"
    assert uncertain.status == "needs_review"
    assert uncertain.facility_id is None


def test_missing_campus_with_multiple_exact_name_region_facilities_needs_review() -> None:
    result = match_facility(
        record(),
        [target("east", campus_name="东院"), target("west", campus_name="西院")],
    )

    assert result.status == "needs_review"
    assert result.reason == "campus_ambiguous"


def test_duplicate_key_is_deterministic_and_never_uses_fuzzy_name() -> None:
    left = record(registration_id=" REG-9 ", registration_id_reliable=True)
    right = record(
        source_record_id="source-2",
        registration_id="REG-9",
        registration_id_reliable=True,
    )
    similar = record(source_record_id="source-3", normalized_name="示例医院分院")

    assert duplicate_key(left) == duplicate_key(right)
    assert duplicate_key(left) is not None
    assert duplicate_key(left) != duplicate_key(similar)
