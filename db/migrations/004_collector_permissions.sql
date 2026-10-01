\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_collector') THEN
    CREATE ROLE eye_collector NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

GRANT USAGE ON SCHEMA app_private TO eye_collector;
GRANT SELECT ON app_private.source_catalog TO eye_collector;
GRANT SELECT ON app_private.import_runs TO eye_collector;
GRANT INSERT (source_id, region_code, status) ON app_private.import_runs TO eye_collector;
GRANT UPDATE (status, ended_at, counts, error_summary)
  ON app_private.import_runs TO eye_collector;
GRANT SELECT ON app_private.source_records TO eye_collector;
GRANT INSERT (source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
  ON app_private.source_records TO eye_collector;

COMMIT;
