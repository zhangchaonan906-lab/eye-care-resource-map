\set ON_ERROR_STOP on
BEGIN;
INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-0000-0000-000000000001', '110000', '北京市', 'province', '2026');
INSERT INTO app_private.organizations (id, canonical_name)
VALUES ('00000000-0000-0000-0000-000000000002', '测试医院');
INSERT INTO app_private.source_catalog (id, name, url, use_basis, status)
VALUES ('00000000-0000-0000-0000-000000000003', '测试来源', 'https://example.org/list', '测试许可', 'approved');
INSERT INTO app_private.facilities
  (id, organization_id, name, normalized_name, category, region_id, address, ophthalmology_status)
VALUES
  ('00000000-0000-0000-0000-000000000004',
   '00000000-0000-0000-0000-000000000002',
   '测试医院东院区', '测试医院东院区', 'general_hospital_ophthalmology',
   '00000000-0000-0000-0000-000000000001', '北京市东城区测试路1号', 'verified');
DO $$
BEGIN
  IF (SELECT count(*) FROM app_private.facilities WHERE name = '测试医院东院区') <> 1 THEN
    RAISE EXCEPTION 'core facility insert failed';
  END IF;
  BEGIN
    INSERT INTO app_private.facilities
      (name, normalized_name, category, region_id, address)
    VALUES ('错误类型', '错误类型', 'bad_category',
      '00000000-0000-0000-0000-000000000001', '测试地址');
    RAISE EXCEPTION 'invalid category was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END $$;
ROLLBACK;
