\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-4000-8000-000000000111', '110000', '北京市', 'province', 'p7-test');
INSERT INTO app_private.source_catalog
  (id, name, url, dataset_page, use_basis, status, data_use_allowed, reuse_allowed, app_display_allowed, permitted_fields, retention_restrictions, source_updated_at)
VALUES ('00000000-0000-4000-8000-000000000112', 'P7 合成来源', 'https://example.org/source',
  'https://example.org/dataset', '仅用于本地合成 API 测试', 'approved', true, true, true, ARRAY['name','address','specialties','coordinates'], 'unrestricted', DATE '2026-09-01');
INSERT INTO app_private.import_runs (id, source_id, region_code, status, ended_at)
VALUES ('00000000-0000-4000-8000-000000000113', '00000000-0000-4000-8000-000000000112', '110000', 'succeeded', now());
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-4000-8000-000000000114', '00000000-0000-4000-8000-000000000112', 'synthetic-1',
  '{"法定代表人":"PRIVATE_PERSON_SENTINEL","负责人":"PRIVATE_PERSON_SENTINEL"}',
  'https://example.org/source/1', repeat('c', 64), '00000000-0000-4000-8000-000000000113');
INSERT INTO app_private.facilities
  (id, name, normalized_name, category, region_id, address, ophthalmology_status,
   verification_status, published_at, last_verified_at)
VALUES ('00000000-0000-4000-8000-000000000115', '合成眼科医院', '合成眼科医院',
  'eye_specialty_hospital', '00000000-0000-4000-8000-000000000111', '合成路1号',
  'verified', 'published', now(), now());
INSERT INTO app_private.facility_locations
  (facility_id, geog_wgs84, coordinate_source_record_id, location_status, verified_at)
VALUES ('00000000-0000-4000-8000-000000000115', ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography,
  '00000000-0000-4000-8000-000000000114', 'verified', now());
INSERT INTO app_private.facility_evidence
  (facility_id, source_record_id, field_name, field_value, confidence)
VALUES
  ('00000000-0000-4000-8000-000000000115', '00000000-0000-4000-8000-000000000114', 'ophthalmology_status', '"verified"'::jsonb, 1),
  ('00000000-0000-4000-8000-000000000115', '00000000-0000-4000-8000-000000000114', 'name', '"合成眼科医院"'::jsonb, 1),
  ('00000000-0000-4000-8000-000000000115', '00000000-0000-4000-8000-000000000114', 'address', '"合成路1号"'::jsonb, 1),
  ('00000000-0000-4000-8000-000000000115', '00000000-0000-4000-8000-000000000114', 'specialties', '"眼科"'::jsonb, 1);

DO $$
DECLARE
  api_row jsonb;
BEGIN
  SELECT to_jsonb(api.*) INTO api_row
  FROM public.published_facility_api AS api
  WHERE api.id = '00000000-0000-4000-8000-000000000115';
  IF api_row IS NULL THEN RAISE EXCEPTION 'verified synthetic facility missing from API view'; END IF;
  IF api_row::text LIKE '%PRIVATE_PERSON_SENTINEL%' OR api_row::text LIKE '%raw_payload%' THEN
    RAISE EXCEPTION 'private source payload leaked into public API view';
  END IF;
  IF api_row->>'normalized_name' <> '合成眼科医院'
     OR api_row->>'longitude_wgs84' <> '116.4'
     OR jsonb_array_length(api_row->'attribution') <> 1 THEN
    RAISE EXCEPTION 'public API view fields or attribution are wrong: %', api_row;
  END IF;
  IF has_table_privilege('eye_public_api', 'app_private.facilities', 'SELECT')
     OR has_table_privilege('eye_public_api', 'app_private.source_records', 'SELECT')
     OR has_table_privilege('eye_public_api', 'app_private.facility_evidence', 'SELECT') THEN
    RAISE EXCEPTION 'public API role can read a private table';
  END IF;
  IF NOT has_table_privilege('eye_public_api', 'public.published_facility_api', 'SELECT') THEN
    RAISE EXCEPTION 'public API role cannot read its public view';
  END IF;
  IF NOT has_function_privilege(
    'eye_public_api',
    'public.query_published_facilities_bbox(double precision, double precision, double precision, double precision, text, text, uuid, integer)',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'public API role cannot execute its bounded bbox query';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.published_facility_api
    WHERE ST_Intersects(geog_wgs84, ST_MakeEnvelope(116.3, 39.8, 116.5, 40.0, 4326)::geography)
  ) THEN
    RAISE EXCEPTION 'PostGIS bbox filter did not return the in-bounds facility';
  END IF;
END $$;
ROLLBACK;
