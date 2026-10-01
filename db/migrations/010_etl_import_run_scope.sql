\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

-- ETL may inspect batch state to validate an explicit P5 manual-only scope.
-- Source policies remain unchanged and import_runs stays read-only for ETL.
REVOKE SELECT ON app_private.import_runs FROM eye_etl;
GRANT SELECT (id, source_id, status) ON app_private.import_runs TO eye_etl;

COMMIT;
