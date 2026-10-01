\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_public_api') THEN
    CREATE ROLE eye_public_api NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

CREATE VIEW public.published_facility_api WITH (security_barrier = true) AS
SELECT
  p.id,
  p.name,
  f.normalized_name,
  p.category,
  p.address,
  p.region_adcode,
  p.region_name,
  p.hospital_level,
  p.hospital_grade,
  p.geog_wgs84,
  p.longitude_wgs84,
  p.latitude_wgs84,
  p.last_verified_at,
  COALESCE(evidence.ophthalmology_evidence_count, 0)::integer AS ophthalmology_evidence_count,
  COALESCE(attribution.items, '[]'::jsonb) AS attribution
FROM public.published_facilities AS p
JOIN app_private.facilities AS f ON f.id = p.id
LEFT JOIN LATERAL (
  SELECT count(*)::integer AS ophthalmology_evidence_count
  FROM app_private.facility_evidence AS e
  JOIN app_private.source_records AS sr ON sr.id = e.source_record_id
  JOIN app_private.source_catalog AS s ON s.id = sr.source_id
  WHERE e.facility_id = f.id
    AND e.field_name = 'ophthalmology_status'
    AND e.field_value = '"verified"'::jsonb
    AND s.status = 'approved'
) AS evidence ON true
LEFT JOIN LATERAL (
  SELECT jsonb_agg(
    jsonb_build_object('name', source_summary.name, 'url', source_summary.url, 'updatedAt', source_summary.updated_at)
    ORDER BY source_summary.name, source_summary.url, source_summary.updated_at
  ) AS items
  FROM (
    SELECT DISTINCT s.name, COALESCE(s.dataset_page, s.url) AS url, s.source_updated_at AS updated_at
    FROM app_private.facility_evidence AS e
    JOIN app_private.source_records AS sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog AS s ON s.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name IN ('name', 'address', 'ophthalmology_status')
      AND s.status = 'approved'
      AND s.app_display_allowed IS TRUE
  ) AS source_summary
) AS attribution ON true;

REVOKE ALL ON public.published_facility_api FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO eye_public_api;
GRANT SELECT ON public.published_facility_api TO eye_public_api;

-- A definer function applies the bbox predicate to the indexed base geography
-- column before joining the published-only API projection.
CREATE FUNCTION public.query_published_facilities_bbox(
  p_west double precision,
  p_south double precision,
  p_east double precision,
  p_north double precision,
  p_category text,
  p_region_prefix text,
  p_after_id uuid,
  p_limit integer
)
RETURNS SETOF public.published_facility_api
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app_private, extensions, pg_temp
AS $$
  SELECT api.*
  FROM app_private.facility_locations AS location
  JOIN public.published_facility_api AS api ON api.id = location.facility_id
  WHERE p_west BETWEEN -180 AND 180
    AND p_east BETWEEN -180 AND 180
    AND p_south BETWEEN -90 AND 90
    AND p_north BETWEEN -90 AND 90
    AND p_west < p_east
    AND p_south < p_north
    AND (p_category IS NULL OR api.category = p_category)
    AND (p_region_prefix IS NULL OR api.region_adcode LIKE p_region_prefix || '%')
    AND (p_after_id IS NULL OR api.id > p_after_id)
    AND p_limit BETWEEN 1 AND 501
    AND public.ST_Intersects(
      location.geog_wgs84,
      public.ST_MakeEnvelope(p_west, p_south, p_east, p_north, 4326)::public.geography
    )
  ORDER BY api.id
  LIMIT p_limit
$$;
REVOKE ALL ON FUNCTION public.query_published_facilities_bbox(
  double precision, double precision, double precision, double precision,
  text, text, uuid, integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.query_published_facilities_bbox(
  double precision, double precision, double precision, double precision,
  text, text, uuid, integer
) TO eye_public_api;
COMMIT;
