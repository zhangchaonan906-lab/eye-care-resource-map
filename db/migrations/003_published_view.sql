\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

CREATE INDEX facilities_published_region_category_idx
  ON app_private.facilities (region_id, category)
  WHERE verification_status = 'published';
CREATE INDEX facilities_normalized_name_idx
  ON app_private.facilities (normalized_name);
CREATE INDEX source_records_source_key_idx
  ON app_private.source_records (source_id, source_key);
CREATE INDEX facility_evidence_facility_field_idx
  ON app_private.facility_evidence (facility_id, field_name);
CREATE INDEX facility_locations_geog_wgs84_idx
  ON app_private.facility_locations USING gist (geog_wgs84);

CREATE VIEW public.published_facilities WITH (security_barrier = true) AS
SELECT
  f.id,
  f.name,
  f.campus_name,
  f.category,
  f.address,
  f.phone,
  f.website,
  f.hospital_level,
  f.hospital_grade,
  r.adcode AS region_adcode,
  r.name AS region_name,
  f.last_verified_at,
  l.geog_wgs84,
  ST_X(l.geog_wgs84::geometry) AS longitude_wgs84,
  ST_Y(l.geog_wgs84::geometry) AS latitude_wgs84
FROM app_private.facilities f
JOIN app_private.regions r ON r.id = f.region_id
JOIN app_private.facility_locations l ON l.facility_id = f.id
JOIN app_private.source_records coordinate_record
  ON coordinate_record.id = l.coordinate_source_record_id
JOIN app_private.source_catalog coordinate_source
  ON coordinate_source.id = coordinate_record.source_id
WHERE f.verification_status = 'published'
  AND f.published_at IS NOT NULL
  AND f.last_verified_at IS NOT NULL
  AND f.ophthalmology_status = 'verified'
  AND l.location_status = 'verified'
  AND l.verified_at IS NOT NULL
  AND coordinate_source.status = 'approved'
  AND EXISTS (
    SELECT 1
    FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog s ON s.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name = 'ophthalmology_status'
      AND e.field_value = '"verified"'::jsonb
      AND s.status = 'approved'
  )
  AND EXISTS (
    SELECT 1
    FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog s ON s.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name = 'name'
      AND e.field_value = to_jsonb(f.name)
      AND s.status = 'approved'
  )
  AND EXISTS (
    SELECT 1
    FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog s ON s.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name = 'address'
      AND e.field_value = to_jsonb(f.address)
      AND s.status = 'approved'
  );

REVOKE ALL ON public.published_facilities FROM PUBLIC;
COMMIT;
