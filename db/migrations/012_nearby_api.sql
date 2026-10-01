\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

CREATE FUNCTION public.query_published_facilities_nearby(
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
  )
  SELECT
    api.id,
    api.name,
    api.normalized_name,
    api.category,
    api.address,
    api.region_adcode,
    api.region_name,
    api.hospital_level,
    api.hospital_grade,
    api.longitude_wgs84,
    api.latitude_wgs84,
    api.ophthalmology_evidence_count,
    api.attribution,
    api.last_verified_at,
    public.ST_Distance(location.geog_wgs84, user_point.geog) AS distance_meters
  FROM app_private.facility_locations AS location
  JOIN public.published_facility_api AS api ON api.id = location.facility_id
  CROSS JOIN user_point
  WHERE p_radius_meters BETWEEN 500 AND 50000
    AND p_limit BETWEEN 2 AND 101
    AND location.location_status = 'verified'
    AND location.verified_at IS NOT NULL
    AND (p_category IS NULL OR api.category = p_category)
    AND public.ST_DWithin(location.geog_wgs84, user_point.geog, p_radius_meters)
  ORDER BY distance_meters ASC, api.id ASC
  LIMIT p_limit
$$;

REVOKE ALL ON FUNCTION public.query_published_facilities_nearby(
  double precision, double precision, double precision, text, integer
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.query_published_facilities_nearby(
  double precision, double precision, double precision, text, integer
) TO eye_public_api;

COMMIT;
