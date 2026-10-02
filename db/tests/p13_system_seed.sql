\set ON_ERROR_STOP on
BEGIN;
INSERT INTO app_private.regions (id,adcode,name,level,version)
VALUES ('00000000-0000-4000-8000-000000001310','110000','P13 合成北京市','province','p13-system')
ON CONFLICT (adcode,version) DO NOTHING;
INSERT INTO app_private.regions (id,adcode,name,level,parent_id,version)
SELECT '00000000-0000-4000-8000-000000001311','110105','P13 合成朝阳区','district',id,'p13-system'
FROM app_private.regions WHERE adcode='110000' AND version='p13-system'
ON CONFLICT (adcode,version) DO NOTHING;
DO $$
DECLARE source_id uuid;
BEGIN
  SELECT id INTO STRICT source_id FROM app_private.source_catalog
  WHERE name='Fixture Directory' AND url='https://fixture.invalid/directory'
    AND status='approved' AND access_policy='automated_access_allowed';

  UPDATE app_private.source_catalog
  SET data_use_allowed=true,
      reuse_allowed=true,
      app_display_allowed=true,
      retention_restrictions='unrestricted',
      permitted_fields=ARRAY['name','address','phone','region','administrative_code',
        'registration_id','campus_name','departments','updated_at','coordinates'],
      attribution_required=true,
      attribution_text='Synthetic fixture data for disposable P13 system QA'
  WHERE id=source_id;

  INSERT INTO app_private.source_sync_policies(
    source_id,region_code,adapter_key,enabled,interval_minutes,run_timeout_seconds,
    max_attempts,backoff_base_seconds,max_backoff_seconds,pause_after_failures,next_due_at
  ) VALUES(source_id,'110000','fixture',true,60,300,3,1,1,4,now()-interval '1 minute');
END;
$$;
COMMIT;
