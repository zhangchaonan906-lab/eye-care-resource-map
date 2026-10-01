\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

-- P5 placeholder exports use an explicit terminal skip disposition. Existing
-- missing_name behavior remains valid for every prior pipeline version.
ALTER TABLE app_private.etl_source_dispositions
  DROP CONSTRAINT etl_source_dispositions_reason_code_check,
  ADD CONSTRAINT etl_source_dispositions_reason_code_check
    CHECK (reason_code IN ('missing_name', 'invalid_name_placeholder'));

ALTER TABLE app_private.import_runs
  ADD COLUMN file_member_name text,
  ADD COLUMN file_member_sha256 text,
  ADD COLUMN file_member_size_bytes bigint,
  ADD CONSTRAINT import_runs_file_member_provenance_complete CHECK (
    (
      file_member_name IS NULL
      AND file_member_sha256 IS NULL
      AND file_member_size_bytes IS NULL
      AND lower(file_original_filename) NOT LIKE '%.zip'
    )
    OR (
      file_member_name IS NOT NULL
      AND file_member_name <> ''
      AND left(file_member_name, 1) <> '/'
      AND position(chr(92) IN file_member_name) = 0
      AND position(':' IN file_member_name) = 0
      AND position('/../' IN file_member_name) = 0
      AND position('/./' IN file_member_name) = 0
      AND left(file_member_name, 3) <> '../'
      AND left(file_member_name, 2) <> './'
      AND right(file_member_name, 3) <> '/..'
      AND right(file_member_name, 2) <> '/.'
      AND lower(file_member_name) LIKE '%.xlsx'
      AND file_member_sha256 ~ '^[0-9a-f]{64}$'
      AND file_member_size_bytes BETWEEN 1 AND 10485760
      AND lower(file_original_filename) LIKE '%.zip'
    )
  );

DO $$
DECLARE
  changed_rows integer;
BEGIN
  UPDATE app_private.source_catalog
  SET permitted_fields = ARRAY[
    'source_fields', 'name', 'address', 'administrative_code',
    'hospital_grade', 'source_category', 'registration_id'
  ]::text[]
  WHERE name = '北京市公共数据开放平台-定点医疗机构信息'
    AND url = 'https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm';
  GET DIAGNOSTICS changed_rows = ROW_COUNT;
  IF changed_rows <> 1 THEN
    RAISE EXCEPTION 'expected exactly one Beijing designated source, updated %', changed_rows;
  END IF;

  UPDATE app_private.source_catalog
  SET permitted_fields = ARRAY[
    'source_fields', 'source_reference_id', 'name', 'administrative_context', 'address',
    'hospital_level', 'hospital_grade', 'source_category', 'specialties',
    'hospital_description'
  ]::text[]
  WHERE name = '深圳市政府数据开放平台-宝安区-医院基本信息'
    AND url = 'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636';
  GET DIAGNOSTICS changed_rows = ROW_COUNT;
  IF changed_rows <> 1 THEN
    RAISE EXCEPTION 'expected exactly one Shenzhen Baoan source, updated %', changed_rows;
  END IF;
END;
$$;

GRANT INSERT (
  file_member_name, file_member_sha256, file_member_size_bytes
) ON app_private.import_runs TO eye_collector;

COMMIT;
