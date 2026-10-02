\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE source_id uuid; import_id uuid;
BEGIN
  SELECT id INTO STRICT source_id FROM app_private.source_catalog
  WHERE name='Fixture Directory' AND url='https://fixture.invalid/directory';
  INSERT INTO app_private.import_runs(source_id,region_code,status,ended_at,counts)
  VALUES(source_id,'110105','succeeded',now(),'{"p13_stress_seed":500}'::jsonb)
  RETURNING id INTO import_id;

  INSERT INTO app_private.source_records(id,source_id,source_key,raw_payload,source_url,content_hash,import_run_id)
  SELECT ('00000000-0000-4000-8001-'||lpad(n::text,12,'0'))::uuid,source_id,'p13-stress-'||n,
    jsonb_build_object('name',format('P13 Synthetic Stress Hospital %s',lpad(n::text,4,'0')),
      'address',format('北京市朝阳区合成压力测试路%s号',n),'departments',jsonb_build_array('眼科')),
    'https://fixture.invalid/stress/'||n,repeat(md5('p13-stress-hash:'||n),2),import_id
  FROM generate_series(1,500) AS n;

  INSERT INTO app_private.facilities(
    id,name,normalized_name,category,region_id,address,ophthalmology_status,
    verification_status,published_at,last_verified_at
  )
  SELECT ('00000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
    format('P13 Synthetic Stress Hospital %s',lpad(n::text,4,'0')),
    lower(format('P13 Synthetic Stress Hospital %s',lpad(n::text,4,'0'))),
    'eye_specialty_hospital',region.id,
    format('北京市朝阳区合成压力测试路%s号',n),'verified','published',now(),now()
  FROM generate_series(1,500) AS n
  CROSS JOIN LATERAL (SELECT id FROM app_private.regions WHERE adcode='110000' ORDER BY valid_from DESC NULLS LAST,version DESC LIMIT 1) AS region;

  INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
  SELECT ('00000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
    ('00000000-0000-4000-8001-'||lpad(n::text,12,'0'))::uuid,e.field_name,e.field_value,1,now()
  FROM generate_series(1,500) AS n
  CROSS JOIN LATERAL (VALUES
    ('name',to_jsonb(format('P13 Synthetic Stress Hospital %s',lpad(n::text,4,'0')))),
    ('address',to_jsonb(format('北京市朝阳区合成压力测试路%s号',n))),
    ('departments','["眼科"]'::jsonb),
    ('ophthalmology_status','"verified"'::jsonb)
  ) AS e(field_name,field_value);

  INSERT INTO app_private.facility_locations(
    facility_id,geog_wgs84,coordinate_source_record_id,accuracy_m,location_status,verified_at
  )
  SELECT ('00000000-0000-4000-8000-'||lpad(n::text,12,'0'))::uuid,
    ST_SetSRID(ST_MakePoint(116.397+(n%25)*0.0002,39.908+(n/25)*0.0002),4326)::geography,
    ('00000000-0000-4000-8001-'||lpad(n::text,12,'0'))::uuid,20,'verified',now()
  FROM generate_series(1,500) AS n;
END;
$$;
COMMIT;
