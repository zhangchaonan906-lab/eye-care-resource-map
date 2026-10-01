\set ON_ERROR_STOP on
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'eye_collector' AND NOT rolcanlogin
      AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
  ) THEN
    RAISE EXCEPTION 'eye_collector must be a non-login, non-superuser role';
  END IF;
  IF NOT has_table_privilege('eye_collector', 'app_private.source_catalog', 'SELECT')
    OR has_table_privilege('eye_collector', 'app_private.source_catalog', 'INSERT') THEN
    RAISE EXCEPTION 'source_catalog must be read-only to the collector';
  END IF;
  IF NOT has_column_privilege('eye_collector', 'app_private.import_runs', 'status', 'UPDATE')
    OR has_column_privilege('eye_collector', 'app_private.import_runs', 'source_id', 'UPDATE') THEN
    RAISE EXCEPTION 'collector import-run updates must be column-scoped';
  END IF;
  IF NOT has_column_privilege(
       'eye_collector', 'app_private.source_records', 'raw_payload', 'INSERT'
     )
    OR has_table_privilege('eye_collector', 'app_private.facilities', 'INSERT')
    OR has_table_privilege('eye_collector', 'app_private.candidate_records', 'INSERT')
    OR has_table_privilege('eye_collector', 'app_private.facility_locations', 'INSERT') THEN
    RAISE EXCEPTION 'collector writes extend beyond source snapshots';
  END IF;
END $$;
