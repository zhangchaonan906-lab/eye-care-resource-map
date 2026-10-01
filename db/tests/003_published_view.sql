\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-0000-0000-000000000021', '110000', '北京市', 'province', '2026');
INSERT INTO app_private.source_catalog (id, name, url, use_basis, status, data_use_allowed, reuse_allowed, app_display_allowed, permitted_fields, retention_restrictions)
VALUES ('00000000-0000-0000-0000-000000000022', '已准入来源', 'https://example.org/source', '测试许可', 'approved', true, true, true, ARRAY['name','address','specialties','coordinates'], 'unrestricted');
INSERT INTO app_private.import_runs (id, source_id, region_code, status, ended_at)
VALUES ('00000000-0000-0000-0000-000000000023',
  '00000000-0000-0000-0000-000000000022', '110000', 'succeeded', now());
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-0000-0000-000000000024',
  '00000000-0000-0000-0000-000000000022', 'eye-1', '{}',
  'https://example.org/source/1', repeat('b', 64),
  '00000000-0000-0000-0000-000000000023');
INSERT INTO app_private.facilities
  (id, name, normalized_name, category, region_id, address,
   ophthalmology_status, verification_status, published_at, last_verified_at)
VALUES
  ('00000000-0000-0000-0000-000000000025', '可见医院', '可见医院',
   'eye_specialty_hospital', '00000000-0000-0000-0000-000000000021',
   '北京市测试路1号', 'verified', 'published', now(), now()),
  ('00000000-0000-0000-0000-000000000026', '缺证据医院', '缺证据医院',
   'eye_specialty_hospital', '00000000-0000-0000-0000-000000000021',
   '北京市测试路2号', 'verified', 'published', now(), now());
INSERT INTO app_private.facility_locations
  (facility_id, geog_wgs84, coordinate_source_record_id, location_status, verified_at)
VALUES
  ('00000000-0000-0000-0000-000000000025',
   ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography,
   '00000000-0000-0000-0000-000000000024', 'verified', now()),
  ('00000000-0000-0000-0000-000000000026',
   ST_SetSRID(ST_MakePoint(116.41, 39.91), 4326)::geography,
   '00000000-0000-0000-0000-000000000024', 'verified', now());
INSERT INTO app_private.facility_evidence
  (facility_id, source_record_id, field_name, field_value, confidence)
VALUES
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'ophthalmology_status',
   '"verified"'::jsonb, 1.0),
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'name',
   '"可见医院"'::jsonb, 1.0),
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'address',
   '"北京市测试路1号"'::jsonb, 1.0),
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'specialties',
   '"眼科"'::jsonb, 1.0);
DO $$
BEGIN
  IF (SELECT count(*) FROM public.published_facilities
      WHERE id IN ('00000000-0000-0000-0000-000000000025',
                   '00000000-0000-0000-0000-000000000026')) <> 1 THEN
    RAISE EXCEPTION 'published view did not enforce evidence gate';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.published_facilities
      WHERE id = '00000000-0000-0000-0000-000000000025'
        AND longitude_wgs84 BETWEEN 116.39 AND 116.41
        AND latitude_wgs84 BETWEEN 39.89 AND 39.91) THEN
    RAISE EXCEPTION 'published location fields are wrong';
  END IF;
END $$;
ROLLBACK;
