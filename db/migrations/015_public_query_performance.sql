\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

-- Materialize bounded spatial/public candidate pages before expanding the
-- attribution-heavy API projection. Search filters facilities before applying
-- the protected publication view, then returns only eligible rows.
CREATE OR REPLACE FUNCTION public.query_published_facilities_bbox(
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
SET search_path = pg_catalog, app_private, public, extensions, pg_temp
AS $$
  WITH spatial_candidates AS MATERIALIZED (
    SELECT location.facility_id
    FROM app_private.facility_locations AS location
    WHERE p_west BETWEEN -180 AND 180
      AND p_east BETWEEN -180 AND 180
      AND p_south BETWEEN -90 AND 90
      AND p_north BETWEEN -90 AND 90
      AND p_west < p_east
      AND p_south < p_north
      AND p_limit BETWEEN 1 AND 501
      AND public.ST_Intersects(
        location.geog_wgs84,
        public.ST_MakeEnvelope(p_west, p_south, p_east, p_north, 4326)::public.geography
      )
  ),
  eligible_facilities AS MATERIALIZED (
    SELECT api.id, api.category, api.region_adcode
    FROM public.published_facilities AS api
  ),
  published_page AS MATERIALIZED (
    SELECT api.id
    FROM spatial_candidates AS spatial
    JOIN eligible_facilities AS api ON api.id = spatial.facility_id
    WHERE (p_category IS NULL OR api.category = p_category)
      AND (p_region_prefix IS NULL OR api.region_adcode LIKE p_region_prefix || '%')
      AND (p_after_id IS NULL OR api.id > p_after_id)
    ORDER BY api.id
    LIMIT p_limit
  ),
  api_rows AS MATERIALIZED (
    SELECT api.* FROM public.published_facility_api AS api
  )
  SELECT api.*
  FROM published_page AS page
  JOIN api_rows AS api ON api.id = page.id
  ORDER BY api.id
$$;

REVOKE ALL ON FUNCTION public.query_published_facilities_bbox(
  double precision, double precision, double precision, double precision,
  text, text, uuid, integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.query_published_facilities_bbox(
  double precision, double precision, double precision, double precision,
  text, text, uuid, integer
) TO eye_public_api;

CREATE OR REPLACE FUNCTION public.query_published_facilities_nearby(
  p_lat double precision,
  p_lng double precision,
  p_radius_meters double precision,
  p_category text,
  p_limit integer
)
RETURNS TABLE (
  id uuid,
  name text,
  normalized_name text,
  category text,
  address text,
  region_adcode text,
  region_name text,
  hospital_level text,
  hospital_grade text,
  longitude_wgs84 double precision,
  latitude_wgs84 double precision,
  ophthalmology_evidence_count integer,
  attribution jsonb,
  last_verified_at timestamptz,
  distance_meters double precision
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app_private, public, extensions, pg_temp
AS $$
  WITH user_point AS MATERIALIZED (
    SELECT public.ST_SetSRID(public.ST_MakePoint(p_lng, p_lat), 4326)::public.geography AS geog
    WHERE p_lat BETWEEN -90 AND 90 AND p_lng BETWEEN -180 AND 180
  ),
  spatial_candidates AS MATERIALIZED (
    SELECT location.facility_id,
           public.ST_Distance(location.geog_wgs84, user_point.geog) AS distance_meters
    FROM app_private.facility_locations AS location
    CROSS JOIN user_point
    WHERE p_radius_meters BETWEEN 500 AND 50000
      AND p_limit BETWEEN 2 AND 101
      AND location.location_status = 'verified'
      AND location.verified_at IS NOT NULL
      AND public.ST_DWithin(location.geog_wgs84, user_point.geog, p_radius_meters)
  ),
  eligible_facilities AS MATERIALIZED (
    SELECT api.id, api.category
    FROM public.published_facilities AS api
  ),
  published_page AS MATERIALIZED (
    SELECT spatial.facility_id, spatial.distance_meters
    FROM spatial_candidates AS spatial
    JOIN eligible_facilities AS eligible ON eligible.id = spatial.facility_id
    WHERE (p_category IS NULL OR eligible.category = p_category)
    ORDER BY spatial.distance_meters ASC, spatial.facility_id ASC
    LIMIT p_limit
  ),
  api_rows AS MATERIALIZED (
    SELECT api.* FROM public.published_facility_api AS api
  )
  SELECT api.id, api.name, api.normalized_name, api.category, api.address,
         api.region_adcode, api.region_name, api.hospital_level, api.hospital_grade,
         api.longitude_wgs84, api.latitude_wgs84, api.ophthalmology_evidence_count,
         api.attribution, api.last_verified_at, page.distance_meters
  FROM published_page AS page
  JOIN api_rows AS api ON api.id = page.facility_id
  ORDER BY page.distance_meters ASC, api.id ASC
$$;

REVOKE ALL ON FUNCTION public.query_published_facilities_nearby(
  double precision, double precision, double precision, text, integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.query_published_facilities_nearby(
  double precision, double precision, double precision, text, integer
) TO eye_public_api;

CREATE OR REPLACE FUNCTION public.query_published_facilities_search(
  p_query text,
  p_match text,
  p_category text,
  p_region_prefix text,
  p_after_name text,
  p_after_id uuid,
  p_limit integer
)
RETURNS SETOF public.published_facility_api
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, app_private, public, extensions, pg_temp
AS $$
  WITH name_candidates AS MATERIALIZED (
    (SELECT f.id, f.normalized_name
     FROM app_private.facilities AS f
     JOIN app_private.regions AS region ON region.id = f.region_id
     WHERE p_match = 'exact'
       AND p_limit BETWEEN 1 AND 101
       AND f.verification_status = 'published' AND f.published_at IS NOT NULL
       AND f.last_verified_at IS NOT NULL AND f.ophthalmology_status = 'verified'
       AND f.normalized_name = p_query
       AND (p_category IS NULL OR f.category = p_category)
       AND (p_region_prefix IS NULL OR region.adcode LIKE p_region_prefix || '%')
       AND (p_after_name IS NULL OR f.normalized_name > p_after_name
         OR (f.normalized_name = p_after_name AND f.id > p_after_id)))
    UNION ALL
    (SELECT f.id, f.normalized_name
     FROM app_private.facilities AS f
     JOIN app_private.regions AS region ON region.id = f.region_id
     WHERE p_match = 'prefix'
       AND p_limit BETWEEN 1 AND 101
       AND f.verification_status = 'published' AND f.published_at IS NOT NULL
       AND f.last_verified_at IS NOT NULL AND f.ophthalmology_status = 'verified'
       AND f.normalized_name LIKE p_query ESCAPE E'\\'
       AND (p_category IS NULL OR f.category = p_category)
       AND (p_region_prefix IS NULL OR region.adcode LIKE p_region_prefix || '%')
       AND (p_after_name IS NULL OR f.normalized_name > p_after_name
         OR (f.normalized_name = p_after_name AND f.id > p_after_id)))
  ),
  published_page AS MATERIALIZED (
    SELECT candidate.id, candidate.normalized_name
    FROM name_candidates AS candidate
    JOIN public.published_facilities AS eligible ON eligible.id = candidate.id
    ORDER BY candidate.normalized_name, candidate.id
    LIMIT p_limit
  ),
  api_rows AS MATERIALIZED (
    SELECT api.* FROM public.published_facility_api AS api
  )
  SELECT api.*
  FROM published_page AS page
  JOIN api_rows AS api ON api.id = page.id
  ORDER BY page.normalized_name, page.id
$$;

REVOKE ALL ON FUNCTION public.query_published_facilities_search(
  text, text, text, text, text, uuid, integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.query_published_facilities_search(
  text, text, text, text, text, uuid, integer
) TO eye_public_api;

COMMIT;
