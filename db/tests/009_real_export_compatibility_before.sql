\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
  affected integer;
  disposition_check text;
BEGIN
  UPDATE app_private.source_catalog
  SET permitted_fields = ARRAY[
    'source_fields', 'name', 'address', 'administrative_context',
    'hospital_grade', 'source_category', 'registration_id'
  ]::text[]
  WHERE name = '北京市公共数据开放平台-定点医疗机构信息'
    AND url = 'https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm';
  GET DIAGNOSTICS affected = ROW_COUNT;
  IF affected <> 1 THEN RAISE EXCEPTION 'Beijing pre-migration source missing'; END IF;

  UPDATE app_private.source_catalog
  SET permitted_fields = ARRAY[
    'source_fields', 'source_reference_id', 'name', 'administrative_context', 'address',
    'hospital_level', 'hospital_grade', 'source_category', 'specialties'
  ]::text[]
  WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息'
    AND url = 'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636';
  GET DIAGNOSTICS affected = ROW_COUNT;
  IF affected <> 1 THEN RAISE EXCEPTION 'Shenzhen pre-migration source missing'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM app_private.source_catalog
    WHERE name = '北京市公共数据开放平台-定点医疗机构信息'
      AND url = 'https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm'
      AND 'administrative_context' = ANY(permitted_fields)
  ) OR NOT EXISTS (
    SELECT 1 FROM app_private.source_catalog
    WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息'
      AND url = 'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636'
      AND NOT ('hospital_description' = ANY(permitted_fields))
  ) THEN
    RAISE EXCEPTION 'unexpected pre-migration permissions';
  END IF;

  SELECT pg_get_constraintdef(oid) INTO disposition_check
  FROM pg_constraint
  WHERE conrelid = 'app_private.etl_source_dispositions'::regclass
    AND conname = 'etl_source_dispositions_reason_code_check';
  IF disposition_check LIKE '%invalid_name_placeholder%' THEN
    RAISE EXCEPTION 'placeholder disposition unexpectedly exists before migration';
  END IF;
END;
$$;
COMMIT;
