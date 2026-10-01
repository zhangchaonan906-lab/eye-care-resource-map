\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

-- Terminal skips are versioned so a future parser version can intentionally retry.
CREATE TABLE app_private.etl_source_dispositions (
  source_record_id uuid NOT NULL REFERENCES app_private.source_records(id),
  pipeline_version text NOT NULL,
  disposition text NOT NULL CHECK (disposition = 'terminal_skip'),
  reason_code text NOT NULL CHECK (reason_code IN ('missing_name')),
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source_record_id, pipeline_version)
);
GRANT SELECT, INSERT ON app_private.etl_source_dispositions TO eye_etl;

-- Keep P3 match candidate lookup bounded to an exact normalized name within a region.
CREATE INDEX facilities_region_normalized_name_idx
  ON app_private.facilities (region_id, normalized_name)
  WHERE verification_status <> 'withdrawn';

CREATE TABLE app_private.geocode_provider_policies (
  provider text NOT NULL,
  provider_version text NOT NULL,
  persistent_storage_allowed boolean NOT NULL,
  quota_per_run integer NOT NULL CHECK (quota_per_run >= 0),
  requests_per_second double precision NOT NULL CHECK (requests_per_second > 0),
  use_basis text NOT NULL,
  reviewed_at timestamptz NOT NULL,
  PRIMARY KEY (provider, provider_version)
);

-- This approval applies only to generated synthetic test coordinates.
INSERT INTO app_private.geocode_provider_policies (
  provider, provider_version, persistent_storage_allowed, quota_per_run,
  requests_per_second, use_basis, reviewed_at
)
VALUES (
  'fixture', 'fixture-v1', true, 1000, 5.0,
  'Locally generated synthetic responses; no external provider terms or data', now()
);

CREATE TABLE app_private.candidate_locations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_record_id uuid NOT NULL,
  source_record_id uuid NOT NULL,
  provider text NOT NULL,
  provider_version text NOT NULL,
  provider_record_id text,
  query_address text NOT NULL,
  query_administrative_code text
    CHECK (query_administrative_code IS NULL OR query_administrative_code ~ '^[0-9]{6}$'),
  address_fingerprint text NOT NULL CHECK (address_fingerprint ~ '^[a-f0-9]{64}$'),
  result_fingerprint text NOT NULL CHECK (result_fingerprint ~ '^[a-f0-9]{64}$'),
  returned_address text,
  returned_adcode text CHECK (returned_adcode IS NULL OR returned_adcode ~ '^[0-9]{6}$'),
  longitude_wgs84 double precision,
  latitude_wgs84 double precision,
  original_coordinate_system text NOT NULL
    CHECK (original_coordinate_system IN ('WGS84', 'GCJ02', 'UNKNOWN')),
  stored_coordinate_system text NOT NULL DEFAULT 'WGS84'
    CHECK (stored_coordinate_system = 'WGS84'),
  accuracy_m integer CHECK (accuracy_m IS NULL OR accuracy_m >= 0),
  precision_level text NOT NULL
    CHECK (precision_level IN ('rooftop', 'building', 'street', 'district', 'city', 'unknown')),
  geocode_result_type text NOT NULL,
  validation_status text NOT NULL
    CHECK (validation_status IN ('verified', 'needs_review', 'rejected')),
  error_code text CHECK (error_code IS NULL OR error_code IN (
    'NO_RESULT', 'AMBIGUOUS_RESULT', 'REGION_MISMATCH', 'LOW_PRECISION',
    'INVALID_COORDINATE', 'RATE_LIMITED', 'PROVIDER_ERROR', 'POLICY_BLOCKED'
  )),
  validation_reason text,
  source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(source_metadata) = 'object'),
  request_at timestamptz NOT NULL,
  retrieval_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  verified_at timestamptz,
  CONSTRAINT candidate_locations_candidate_source_fk
    FOREIGN KEY (candidate_record_id, source_record_id)
    REFERENCES app_private.candidate_records(id, source_record_id),
  CONSTRAINT candidate_locations_provider_policy_fk
    FOREIGN KEY (provider, provider_version)
    REFERENCES app_private.geocode_provider_policies(provider, provider_version),
  CONSTRAINT candidate_locations_coordinate_pair_check
    CHECK ((longitude_wgs84 IS NULL) = (latitude_wgs84 IS NULL)),
  CONSTRAINT candidate_locations_world_bounds_check
    CHECK (
      (longitude_wgs84 IS NULL AND latitude_wgs84 IS NULL)
      OR (longitude_wgs84 BETWEEN -180 AND 180 AND latitude_wgs84 BETWEEN -90 AND 90)
    ),
  CONSTRAINT candidate_locations_verified_guard_check
    CHECK (
      validation_status <> 'verified'
      OR (
        longitude_wgs84 IS NOT NULL
        AND longitude_wgs84 BETWEEN 73.5 AND 135.1
        AND latitude_wgs84 BETWEEN 18.0 AND 53.6
        AND NOT (longitude_wgs84 BETWEEN -0.01 AND 0.01
                 AND latitude_wgs84 BETWEEN -0.01 AND 0.01)
        AND stored_coordinate_system = 'WGS84'
        AND precision_level IN ('rooftop', 'building')
        AND accuracy_m BETWEEN 0 AND 100
        AND returned_adcode IS NOT NULL
        AND error_code IS NULL
        AND validation_reason IS NULL
        AND verified_at IS NOT NULL
      )
    )
);

CREATE UNIQUE INDEX candidate_locations_provider_result_uq
  ON app_private.candidate_locations (
    candidate_record_id, provider, provider_version, address_fingerprint, result_fingerprint
  );
CREATE INDEX candidate_locations_candidate_status_idx
  ON app_private.candidate_locations (candidate_record_id, validation_status, created_at DESC);
CREATE INDEX etl_source_dispositions_version_idx
  ON app_private.etl_source_dispositions (pipeline_version, processed_at);

CREATE FUNCTION app_private.enforce_geocode_provider_policy()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  storage_allowed boolean;
BEGIN
  SELECT persistent_storage_allowed INTO storage_allowed
  FROM app_private.geocode_provider_policies
  WHERE provider = NEW.provider AND provider_version = NEW.provider_version;

  IF storage_allowed IS NULL THEN
    RAISE EXCEPTION 'geocode provider policy is missing'
      USING ERRCODE = '23514';
  END IF;

  IF NOT storage_allowed AND (
    NEW.provider_record_id IS NOT NULL
    OR NEW.returned_address IS NOT NULL
    OR NEW.returned_adcode IS NOT NULL
    OR NEW.longitude_wgs84 IS NOT NULL
    OR NEW.latitude_wgs84 IS NOT NULL
    OR NEW.accuracy_m IS NOT NULL
    OR NEW.source_metadata <> '{}'::jsonb
  ) THEN
    RAISE EXCEPTION 'provider policy blocks persistence of provider response data'
      USING ERRCODE = '23514';
  END IF;

  IF NOT storage_allowed AND (
    NEW.validation_status <> 'needs_review'
    OR NEW.error_code IS DISTINCT FROM 'POLICY_BLOCKED'
  ) THEN
    RAISE EXCEPTION 'provider policy block must be recorded as needs_review'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER candidate_location_provider_policy_trg
BEFORE INSERT OR UPDATE ON app_private.candidate_locations
FOR EACH ROW EXECUTE FUNCTION app_private.enforce_geocode_provider_policy();

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_geocode') THEN
    CREATE ROLE eye_geocode NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

GRANT USAGE ON SCHEMA app_private TO eye_geocode;
GRANT SELECT ON app_private.candidate_records TO eye_geocode;
GRANT SELECT ON app_private.candidate_evidence TO eye_geocode;
GRANT SELECT ON app_private.regions TO eye_geocode;
GRANT SELECT ON app_private.geocode_provider_policies TO eye_geocode;
GRANT SELECT ON app_private.candidate_locations TO eye_geocode;
GRANT INSERT (
  candidate_record_id, source_record_id, provider, provider_version,
  provider_record_id, query_address, query_administrative_code,
  address_fingerprint, result_fingerprint, returned_address, returned_adcode,
  longitude_wgs84, latitude_wgs84, original_coordinate_system,
  stored_coordinate_system, accuracy_m, precision_level, geocode_result_type,
  validation_status, error_code, validation_reason, source_metadata,
  request_at, retrieval_at, verified_at
) ON app_private.candidate_locations TO eye_geocode;

COMMIT;
