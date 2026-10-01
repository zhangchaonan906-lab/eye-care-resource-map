\set ON_ERROR_STOP on
DO $$
DECLARE
  policy_default text;
BEGIN
  IF (SELECT count(*) FROM app_private.source_catalog
      WHERE url IN ('https://legacy.invalid/unknown', 'https://legacy.invalid/null')
        AND access_policy = 'manual_review_required') <> 2 THEN
    RAISE EXCEPTION 'unknown and null legacy access policies must fail closed';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app_private.source_catalog
      WHERE url = 'https://legacy.invalid/manual' AND access_policy = 'manual_only') THEN
    RAISE EXCEPTION 'manual_only must remain compatible';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM app_private.source_catalog
      WHERE access_policy = 'automated_access_allowed') THEN
    RAISE EXCEPTION 'automated_access_allowed must remain compatible';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_etl' AND NOT rolcanlogin
      AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole) THEN
    RAISE EXCEPTION 'eye_etl must be a non-login least-privilege role';
  END IF;
  IF NOT has_table_privilege('eye_etl', 'app_private.source_records', 'SELECT')
    OR has_table_privilege('eye_etl', 'app_private.source_records', 'UPDATE')
    OR has_table_privilege('eye_etl', 'app_private.source_records', 'DELETE')
    OR has_table_privilege('eye_etl', 'app_private.facilities', 'INSERT')
    OR has_table_privilege('eye_etl', 'app_private.facilities', 'UPDATE') THEN
    RAISE EXCEPTION 'ETL privileges exceed the candidate pipeline boundary';
  END IF;
  IF NOT has_column_privilege(
       'eye_etl', 'app_private.candidate_records', 'source_record_id', 'INSERT'
     )
    OR NOT has_column_privilege(
       'eye_etl', 'app_private.candidate_evidence', 'candidate_record_id', 'INSERT'
     )
    OR NOT has_column_privilege('eye_etl', 'app_private.duplicate_cases', 'reason', 'INSERT')
    OR NOT has_column_privilege(
       'eye_etl', 'app_private.duplicate_case_candidates', 'duplicate_case_id', 'INSERT'
     ) THEN
    RAISE EXCEPTION 'ETL role is missing candidate or review-queue writes';
  END IF;
  IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = 'app_private.source_catalog'::regclass
        AND conname = 'source_catalog_access_policy_check'
        AND contype = 'c'
    ) THEN
    RAISE EXCEPTION 'structured access policy check is missing';
  END IF;
  SELECT pg_get_expr(d.adbin, d.adrelid) INTO policy_default
  FROM pg_attribute a
  JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
  WHERE a.attrelid = 'app_private.source_catalog'::regclass
    AND a.attname = 'access_policy';
  IF policy_default IS NULL OR policy_default NOT LIKE '%manual_review_required%' THEN
    RAISE EXCEPTION 'access policy default must fail closed';
  END IF;
  IF NOT EXISTS (
      SELECT 1 FROM pg_trigger
      WHERE tgrelid = 'app_private.source_records'::regclass
        AND tgname = 'source_records_immutable_trg' AND NOT tgisinternal
    ) THEN
    RAISE EXCEPTION 'source records immutable trigger is missing';
  END IF;
  IF NOT EXISTS (
      SELECT 1 FROM pg_trigger
      WHERE tgrelid = 'app_private.duplicate_cases'::regclass
        AND tgname = 'duplicate_case_min_members_trg' AND NOT tgisinternal
    ) OR NOT EXISTS (
      SELECT 1 FROM pg_trigger
      WHERE tgrelid = 'app_private.duplicate_case_candidates'::regclass
        AND tgname = 'duplicate_case_candidate_min_members_trg' AND NOT tgisinternal
    ) THEN
    RAISE EXCEPTION 'duplicate cases must enforce the minimum member count';
  END IF;
END $$;

INSERT INTO app_private.source_catalog (name, url, use_basis, status)
VALUES ('Default policy test', 'https://policy.invalid/default', 'synthetic test', 'pending');
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM app_private.source_catalog
      WHERE url = 'https://policy.invalid/default'
        AND access_policy = 'manual_review_required') THEN
    RAISE EXCEPTION 'new source rows must default to a blocked review policy';
  END IF;
  BEGIN
    UPDATE app_private.source_catalog SET access_policy = 'unexpected-policy'
    WHERE url = 'https://policy.invalid/default';
    RAISE EXCEPTION 'unknown access policy was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END $$;
DELETE FROM app_private.source_catalog WHERE url = 'https://policy.invalid/default';

BEGIN;
WITH registered_source AS (
  INSERT INTO app_private.source_catalog (name, url, use_basis, status)
  VALUES ('Immutable snapshot test', 'https://immutable.invalid/catalog',
    'synthetic database test', 'pending')
  RETURNING id
), created_run AS (
  INSERT INTO app_private.import_runs (source_id, region_code, status)
  SELECT id, '110000', 'running' FROM registered_source
  RETURNING id
)
INSERT INTO app_private.source_records
  (source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
SELECT registered_source.id, 'immutable-test', '{"name":"Original"}'::jsonb,
  'https://immutable.invalid/record', repeat('a', 64), created_run.id
FROM created_run
CROSS JOIN registered_source;

DO $$
BEGIN
  BEGIN
    UPDATE app_private.source_records SET raw_payload = '{"name":"Changed"}'::jsonb
    WHERE source_key = 'immutable-test';
    RAISE EXCEPTION 'source record update was accepted';
  EXCEPTION WHEN SQLSTATE '55000' THEN
    NULL;
  END;
  BEGIN
    DELETE FROM app_private.source_records WHERE source_key = 'immutable-test';
    RAISE EXCEPTION 'source record delete was accepted';
  EXCEPTION WHEN SQLSTATE '55000' THEN
    NULL;
  END;
  IF (SELECT raw_payload FROM app_private.source_records
      WHERE source_key = 'immutable-test') <> '{"name":"Original"}'::jsonb THEN
    RAISE EXCEPTION 'source record changed after rejected mutation';
  END IF;
END $$;
ROLLBACK;
