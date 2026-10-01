\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

DO $$
DECLARE
  nearby_function regprocedure := 'public.query_published_facilities_nearby(double precision,double precision,double precision,text,integer)'::regprocedure;
BEGIN
  IF NOT has_function_privilege('eye_public_api', nearby_function, 'EXECUTE') THEN
    RAISE EXCEPTION 'eye_public_api cannot execute nearby query function';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM pg_proc AS proc
    CROSS JOIN LATERAL aclexplode(coalesce(proc.proacl, acldefault('f', proc.proowner))) AS acl
    WHERE proc.oid = nearby_function
      AND acl.grantee = 0
      AND acl.privilege_type = 'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'PUBLIC can execute nearby query function';
  END IF;
  IF has_table_privilege('eye_public_api', 'app_private.facilities', 'SELECT')
     OR has_table_privilege('eye_public_api', 'app_private.facility_locations', 'SELECT')
     OR has_table_privilege('eye_public_api', 'app_private.facilities', 'INSERT')
     OR has_table_privilege('eye_public_api', 'app_private.facilities', 'UPDATE')
     OR has_table_privilege('eye_public_api', 'app_private.source_records', 'SELECT')
     OR has_table_privilege('eye_public_api', 'app_private.source_records', 'INSERT')
     OR has_table_privilege('eye_public_api', 'app_private.source_records', 'UPDATE')
     OR has_table_privilege('eye_public_api', 'app_private.facility_evidence', 'SELECT') THEN
    RAISE EXCEPTION 'eye_public_api can read private source/facility tables';
  END IF;
END $$;

ROLLBACK;
