\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
  beijing_fields text[];
  shenzhen_fields text[];
  disposition_check text;
BEGIN
  SELECT permitted_fields INTO beijing_fields
  FROM app_private.source_catalog
  WHERE name = '北京市公共数据开放平台-定点医疗机构信息'
    AND url = 'https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm';
  IF beijing_fields IS NULL
     OR NOT beijing_fields @> ARRAY[
       'source_fields', 'name', 'address', 'administrative_code',
       'hospital_grade', 'source_category', 'registration_id'
     ]::text[]
     OR 'administrative_context' = ANY(beijing_fields) THEN
    RAISE EXCEPTION 'Beijing official export permissions were not migrated';
  END IF;

  SELECT permitted_fields INTO shenzhen_fields
  FROM app_private.source_catalog
  WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息'
    AND url = 'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636';
  IF shenzhen_fields IS NULL
     OR NOT shenzhen_fields @> ARRAY[
       'source_fields', 'source_reference_id', 'name', 'administrative_context',
       'address', 'source_category', 'hospital_level', 'hospital_grade',
       'specialties', 'hospital_description'
     ]::text[] THEN
    RAISE EXCEPTION 'Shenzhen official export permissions were not migrated';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'app_private' AND table_name = 'import_runs'
      AND column_name = 'file_member_sha256'
  ) THEN
    RAISE EXCEPTION 'archive member provenance columns are missing';
  END IF;

  SELECT pg_get_constraintdef(oid) INTO disposition_check
  FROM pg_constraint
  WHERE conrelid = 'app_private.etl_source_dispositions'::regclass
    AND conname = 'etl_source_dispositions_reason_code_check';
  IF disposition_check NOT LIKE '%invalid_name_placeholder%' THEN
    RAISE EXCEPTION 'placeholder disposition reason was not enabled';
  END IF;
END;
$$;
COMMIT;
