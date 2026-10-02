\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

INSERT INTO app_private.regions(id,adcode,name,level,version)
VALUES('00000000-0000-4000-8000-000000001400','110000','P14 合成地区','province','p14-restore-drill');
INSERT INTO app_private.source_catalog(
  id,name,url,use_basis,status,permitted_fields,access_policy,data_use_allowed,reuse_allowed,
  app_display_allowed,raw_data_transfer_allowed,raw_data_redistribution_allowed,attribution_required,
  attribution_text,retention_restrictions
)
VALUES(
  '00000000-0000-4000-8000-000000001401','P14 Synthetic Restore Fixture',
  'https://fixture.invalid/p14-restore','Generated synthetic data for disposable backup restore test',
  'approved',ARRAY['name','address','specialties','coordinates'],
  'manual_only',true,true,true,false,false,false,'P14 synthetic fixture','unrestricted'
);
INSERT INTO app_private.import_runs(id,source_id,region_code,status,ended_at)
VALUES('00000000-0000-4000-8000-000000001402','00000000-0000-4000-8000-000000001401','110000','succeeded',now());
INSERT INTO app_private.source_records(id,source_id,source_key,raw_payload,source_url,content_hash,import_run_id)
VALUES(
  '00000000-0000-4000-8000-000000001403','00000000-0000-4000-8000-000000001401','p14-restore-fixture-1',
  '{"name":"P14 合成眼科机构","address":"合成测试路 1 号"}',
  'https://fixture.invalid/p14-restore/1',repeat('a',64),'00000000-0000-4000-8000-000000001402'
);
INSERT INTO app_private.facilities(
  id,name,normalized_name,category,region_id,address,ophthalmology_status,
  verification_status,published_at,last_verified_at
)
VALUES(
  '00000000-0000-4000-8000-000000001404','P14 合成眼科机构','p14 合成眼科机构',
  'eye_specialty_hospital','00000000-0000-4000-8000-000000001400','合成测试路 1 号',
  'verified','published',now(),now()
);
INSERT INTO app_private.facility_locations(facility_id,geog_wgs84,coordinate_source_record_id,location_status,verified_at)
VALUES(
  '00000000-0000-4000-8000-000000001404',
  ST_SetSRID(ST_MakePoint(116.4,39.9),4326)::geography,
  '00000000-0000-4000-8000-000000001403','verified',now()
);
INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence)
VALUES
  ('00000000-0000-4000-8000-000000001404','00000000-0000-4000-8000-000000001403','name','"P14 合成眼科机构"'::jsonb,1),
  ('00000000-0000-4000-8000-000000001404','00000000-0000-4000-8000-000000001403','address','"合成测试路 1 号"'::jsonb,1),
  ('00000000-0000-4000-8000-000000001404','00000000-0000-4000-8000-000000001403','ophthalmology_status','"verified"'::jsonb,1),
  ('00000000-0000-4000-8000-000000001404','00000000-0000-4000-8000-000000001403','specialties','"眼科"'::jsonb,1);
COMMIT;
