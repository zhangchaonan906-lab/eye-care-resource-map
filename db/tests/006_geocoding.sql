\set ON_ERROR_STOP on
DO $$
BEGIN
  IF to_regclass('app_private.candidate_locations') IS NULL THEN
    RAISE EXCEPTION 'candidate coordinate staging table is required';
  END IF;
  IF to_regclass('app_private.etl_source_dispositions') IS NULL THEN
    RAISE EXCEPTION 'terminal ETL dispositions are required';
  END IF;
  IF to_regclass('app_private.geocode_provider_policies') IS NULL THEN
    RAISE EXCEPTION 'geocode provider policy gate is required';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'eye_geocode' AND NOT rolcanlogin
      AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
  ) THEN
    RAISE EXCEPTION 'eye_geocode must be a least-privilege NOLOGIN role';
  END IF;
  IF NOT has_table_privilege('eye_geocode', 'app_private.candidate_records', 'SELECT')
    OR NOT has_table_privilege('eye_geocode', 'app_private.regions', 'SELECT')
    OR NOT has_table_privilege('eye_geocode', 'app_private.candidate_evidence', 'SELECT')
    OR NOT has_table_privilege('eye_geocode', 'app_private.geocode_provider_policies', 'SELECT')
    OR NOT has_table_privilege('eye_geocode', 'app_private.candidate_locations', 'SELECT')
    OR NOT has_column_privilege(
      'eye_geocode', 'app_private.candidate_locations', 'candidate_record_id', 'INSERT'
    ) THEN
    RAISE EXCEPTION 'eye_geocode is missing required staging privileges';
  END IF;
  IF has_table_privilege('eye_geocode', 'app_private.source_records', 'UPDATE')
    OR has_table_privilege('eye_geocode', 'app_private.source_records', 'DELETE')
    OR has_table_privilege('eye_geocode', 'app_private.facilities', 'INSERT')
    OR has_table_privilege('eye_geocode', 'app_private.facilities', 'UPDATE')
    OR has_table_privilege('eye_geocode', 'app_private.facility_locations', 'INSERT')
    OR has_table_privilege('eye_geocode', 'app_private.facility_locations', 'UPDATE')
    OR has_table_privilege('eye_geocode', 'public.published_facilities', 'INSERT') THEN
    RAISE EXCEPTION 'geocode role exceeds candidate coordinate staging boundary';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'app_private.candidate_locations'::regclass
      AND conname = 'candidate_locations_verified_guard_check'
  ) THEN
    RAISE EXCEPTION 'verified coordinates must have database-level validation guards';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'app_private'
      AND indexname = 'candidate_locations_provider_result_uq'
  ) THEN
    RAISE EXCEPTION 'candidate coordinate result fingerprint must be unique';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'app_private'
      AND indexname = 'facilities_region_normalized_name_idx'
  ) THEN
    RAISE EXCEPTION 'P3 exact region and name candidate lookup must be indexed';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'app_private.candidate_locations'::regclass
      AND tgname = 'candidate_location_provider_policy_trg'
      AND NOT tgisinternal
  ) THEN
    RAISE EXCEPTION 'coordinate persistence must be guarded by provider policy';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM app_private.geocode_provider_policies
    WHERE provider = 'fixture' AND provider_version = 'fixture-v1'
      AND persistent_storage_allowed
  ) THEN
    RAISE EXCEPTION 'only the synthetic fixture provider is approved for coordinate persistence';
  END IF;
  IF has_table_privilege('eye_geocode', 'app_private.geocode_provider_policies', 'UPDATE')
    OR has_table_privilege('eye_geocode', 'app_private.geocode_provider_policies', 'INSERT')
    OR has_table_privilege('eye_geocode', 'app_private.candidate_locations', 'UPDATE')
    OR has_table_privilege('eye_geocode', 'app_private.candidate_locations', 'DELETE') THEN
    RAISE EXCEPTION 'geocode runtime must not approve its own provider policy';
  END IF;
END $$;
