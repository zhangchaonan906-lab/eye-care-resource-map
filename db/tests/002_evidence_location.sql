\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-0000-0000-000000000011', '440000', '广东省', 'province', '2026');
INSERT INTO app_private.source_catalog (id, name, url, use_basis, status)
VALUES ('00000000-0000-0000-0000-000000000012', '测试来源', 'https://example.org/guangdong', '测试许可', 'approved');
INSERT INTO app_private.facilities
  (id, name, normalized_name, category, region_id, address, ophthalmology_status)
VALUES ('00000000-0000-0000-0000-000000000013', '测试眼科医院', '测试眼科医院',
  'eye_specialty_hospital', '00000000-0000-0000-0000-000000000011',
  '广州市测试路1号', 'verified');
INSERT INTO app_private.import_runs (id, source_id, region_code, status)
VALUES ('00000000-0000-0000-0000-000000000014',
  '00000000-0000-0000-0000-000000000012', '440000', 'running');
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-0000-0000-000000000015',
  '00000000-0000-0000-0000-000000000012', 'hospital-1', '{"name":"测试眼科医院"}',
  'https://example.org/guangdong/1', repeat('a', 64),
  '00000000-0000-0000-0000-000000000014');
INSERT INTO app_private.facility_evidence
  (facility_id, source_record_id, field_name, field_value, confidence)
VALUES ('00000000-0000-0000-0000-000000000013',
  '00000000-0000-0000-0000-000000000015', 'ophthalmology_status',
  '"verified"'::jsonb, 1.0);
INSERT INTO app_private.facility_locations
  (facility_id, geog_wgs84, coordinate_source_id, location_status)
VALUES ('00000000-0000-0000-0000-000000000013',
  ST_SetSRID(ST_MakePoint(113.2644, 23.1291), 4326)::geography,
  '00000000-0000-0000-0000-000000000012', 'verified');
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM app_private.facility_locations
    WHERE facility_id = '00000000-0000-0000-0000-000000000013'
      AND ST_DWithin(geog_wgs84,
        ST_SetSRID(ST_MakePoint(113.2644, 23.1291), 4326)::geography, 10)
  ) THEN
    RAISE EXCEPTION 'WGS84 nearby query failed';
  END IF;
  BEGIN
    INSERT INTO app_private.source_records
      (source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
    VALUES ('00000000-0000-0000-0000-000000000012', 'hospital-1', '{}',
      'https://example.org/guangdong/1', repeat('a', 64),
      '00000000-0000-0000-0000-000000000014');
    RAISE EXCEPTION 'duplicate source snapshot was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END $$;
ROLLBACK;
