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
  (facility_id, geog_wgs84, coordinate_source_record_id, location_status)
VALUES ('00000000-0000-0000-0000-000000000013',
  ST_SetSRID(ST_MakePoint(113.2644, 23.1291), 4326)::geography,
  '00000000-0000-0000-0000-000000000015', 'verified');
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
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-0000-0000-000000000016',
  '00000000-0000-0000-0000-000000000012', 'hospital-2', '{}',
  'https://example.org/guangdong/2', repeat('b', 64),
  '00000000-0000-0000-0000-000000000014');
INSERT INTO app_private.candidate_records
  (id, source_record_id, parsed_fields, match_status, proposed_facility_id)
VALUES
  ('00000000-0000-0000-0000-000000000017',
   '00000000-0000-0000-0000-000000000015', '{}', 'matched',
   '00000000-0000-0000-0000-000000000013'),
  ('00000000-0000-0000-0000-000000000018',
   '00000000-0000-0000-0000-000000000016', '{}', 'unmatched', NULL);
-- Pending cases may be assembled one membership at a time.
INSERT INTO app_private.duplicate_cases (id, reason)
VALUES ('00000000-0000-0000-0000-000000000019', '测试重复候选');
INSERT INTO app_private.duplicate_case_candidates (duplicate_case_id, candidate_record_id)
VALUES
  ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000017'),
  ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000018');
INSERT INTO app_private.import_runs (source_id, region_code, status, ended_at)
VALUES ('00000000-0000-0000-0000-000000000012', '440000', 'succeeded', now());
DO $$
BEGIN
  IF (SELECT count(*) FROM app_private.duplicate_case_candidates
      WHERE duplicate_case_id = '00000000-0000-0000-0000-000000000019') <> 2 THEN
    RAISE EXCEPTION 'duplicate case membership count is wrong';
  END IF;
  BEGIN
    INSERT INTO app_private.duplicate_case_candidates VALUES
      ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000099');
    RAISE EXCEPTION 'nonexistent candidate membership was accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO app_private.duplicate_case_candidates VALUES
      ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000017');
    RAISE EXCEPTION 'duplicate candidate membership was accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.candidate_records SET proposed_facility_id = NULL
      WHERE id = '00000000-0000-0000-0000-000000000017';
    RAISE EXCEPTION 'matched candidate without facility was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.candidate_records
      SET proposed_facility_id = '00000000-0000-0000-0000-000000000013'
      WHERE id = '00000000-0000-0000-0000-000000000018';
    RAISE EXCEPTION 'unmatched candidate with facility was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.candidate_records SET match_status = 'rejected'
      WHERE id = '00000000-0000-0000-0000-000000000017';
    RAISE EXCEPTION 'rejected candidate with facility was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  UPDATE app_private.candidate_records SET match_status = 'needs_review'
    WHERE id IN ('00000000-0000-0000-0000-000000000017', '00000000-0000-0000-0000-000000000018');
  UPDATE app_private.candidate_records SET match_status = 'rejected'
    WHERE id = '00000000-0000-0000-0000-000000000018';
  BEGIN
    INSERT INTO app_private.import_runs (source_id, region_code, status)
    VALUES ('00000000-0000-0000-0000-000000000012', '440000', 'failed');
    RAISE EXCEPTION 'terminal import without ended_at was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO app_private.import_runs (source_id, region_code, status, ended_at)
    VALUES ('00000000-0000-0000-0000-000000000012', '440000', 'running', now());
    RAISE EXCEPTION 'running import with ended_at was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO app_private.import_runs (source_id, region_code, status)
    VALUES ('00000000-0000-0000-0000-000000000012', '44000', 'running');
    RAISE EXCEPTION 'invalid import region code was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.facility_locations
      SET coordinate_source_record_id = '00000000-0000-0000-0000-000000000099'
      WHERE facility_id = '00000000-0000-0000-0000-000000000013';
    RAISE EXCEPTION 'nonexistent coordinate source record was accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
  DELETE FROM app_private.duplicate_cases WHERE id = '00000000-0000-0000-0000-000000000019';
  IF EXISTS (SELECT 1 FROM app_private.duplicate_case_candidates
      WHERE duplicate_case_id = '00000000-0000-0000-0000-000000000019') THEN
    RAISE EXCEPTION 'duplicate case deletion did not cascade';
  END IF;
END $$;
ROLLBACK;
