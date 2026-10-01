\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

DO $$
DECLARE
  beijing_count integer;
  shenzhen_row app_private.source_catalog%ROWTYPE;
BEGIN
  SELECT count(*) INTO beijing_count
  FROM app_private.source_catalog
  WHERE name IN (
    '北京市公共数据开放平台-医院',
    '北京市公共数据开放平台-定点医疗机构信息'
  )
    AND status = 'approved'
    AND access_policy = 'manual_only'
    AND data_use_allowed IS TRUE
    AND reuse_allowed IS TRUE
    AND app_display_allowed IS TRUE
    AND raw_data_transfer_allowed IS TRUE
    AND attribution_required IS TRUE
    AND attribution_text = '北京市公共数据开放平台';
  IF beijing_count <> 2 THEN
    RAISE EXCEPTION 'both Beijing open data sources must be individually approved';
  END IF;

  SELECT * INTO shenzhen_row
  FROM app_private.source_catalog
  WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息';
  IF NOT FOUND OR shenzhen_row.status <> 'approved'
     OR shenzhen_row.data_use_allowed IS NOT TRUE
     OR shenzhen_row.reuse_allowed IS NOT TRUE
     OR shenzhen_row.app_display_allowed IS NOT TRUE
     OR shenzhen_row.raw_data_transfer_allowed IS NOT FALSE
     OR shenzhen_row.raw_data_redistribution_allowed IS NOT FALSE
     OR shenzhen_row.attribution_required IS NOT TRUE
     OR shenzhen_row.attribution_text <> '深圳市政府数据开放平台'
     OR shenzhen_row.retention_restrictions <> 'delete_on_withdrawal'
     OR shenzhen_row.pilot_group_record_limit <> 300 THEN
    RAISE EXCEPTION 'Shenzhen source rights or retention controls are incomplete';
  END IF;
END;
$$;

SAVEPOINT pilot_limit_test;
DO $$
DECLARE
  source_id uuid;
  run_id uuid;
  rejected boolean := false;
BEGIN
  SELECT id INTO source_id FROM app_private.source_catalog
  WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息';
  UPDATE app_private.source_catalog SET pilot_group_record_limit = 1 WHERE id = source_id;
  INSERT INTO app_private.import_runs (source_id, region_code, status)
  VALUES (source_id, '440306', 'running') RETURNING id INTO run_id;
  INSERT INTO app_private.source_records (
    source_id, source_key, raw_payload, source_url, content_hash, import_run_id
  ) VALUES (
    source_id, 'limit-test-1', '{"name":"合成测试医院"}'::jsonb,
    'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636',
    repeat('b', 64), run_id
  );
  BEGIN
    INSERT INTO app_private.source_records (
      source_id, source_key, raw_payload, source_url, content_hash, import_run_id
    )
    SELECT id, 'limit-test-2', '{"name":"合成测试医院二"}'::jsonb, url, repeat('c', 64), run_id
    FROM app_private.source_catalog
    WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息';
  EXCEPTION WHEN check_violation THEN
    rejected := true;
  END;
  IF NOT rejected THEN
    RAISE EXCEPTION 'pilot aggregate record limit was not enforced';
  END IF;
END;
$$;
ROLLBACK TO SAVEPOINT pilot_limit_test;

DO $$
DECLARE
  source_id uuid;
  run_id uuid;
  erased bigint;
  record_id uuid;
  candidate_id uuid;
BEGIN
  SELECT id INTO source_id FROM app_private.source_catalog
  WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息';
  UPDATE app_private.source_catalog SET status = 'suspended' WHERE id = source_id;
  INSERT INTO app_private.import_runs (source_id, region_code, status)
  VALUES (source_id, '440306', 'running') RETURNING id INTO run_id;
  INSERT INTO app_private.source_records (
    source_id, source_key, raw_payload, source_url, content_hash, import_run_id
  ) VALUES (
    source_id, 'retention-test', '{"name":"合成测试医院"}'::jsonb,
    'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636',
    repeat('a', 64), run_id
  ) RETURNING id INTO record_id;
  INSERT INTO app_private.candidate_records (source_record_id, parsed_fields)
  VALUES (record_id, '{"name":"合成测试医院"}'::jsonb) RETURNING id INTO candidate_id;

  erased := app_private.erase_withdrawn_source_records(source_id);
  IF erased <> 1
     OR EXISTS (SELECT 1 FROM app_private.source_records WHERE id = record_id)
     OR EXISTS (SELECT 1 FROM app_private.candidate_records WHERE id = candidate_id)
     OR NOT EXISTS (
       SELECT 1 FROM app_private.audit_events
       WHERE entity_id = source_id AND action = 'withdrawn_source_data_erased'
     ) THEN
    RAISE EXCEPTION 'withdrawn source data purge did not remove snapshots and audit safely';
  END IF;
END;
$$;

ROLLBACK;
