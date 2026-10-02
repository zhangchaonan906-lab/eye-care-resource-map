\set ON_ERROR_STOP on
BEGIN;
INSERT INTO app_private.regions(id,adcode,name,level,version)
VALUES('00000000-0000-4000-8000-000000000901','110000','测试省','province','p11-test');
INSERT INTO app_private.source_catalog(id,name,url,dataset_page,use_basis,status,data_use_allowed,reuse_allowed,app_display_allowed,permitted_fields,retention_restrictions)
VALUES('00000000-0000-4000-8000-000000000902','P11 synthetic source','https://example.test/source','https://example.test/dataset','synthetic only','pending',true,true,true,ARRAY['name','address','specialties','coordinates'],'unrestricted');
INSERT INTO app_private.import_runs(id,source_id,region_code,status,ended_at)
VALUES('00000000-0000-4000-8000-000000000903','00000000-0000-4000-8000-000000000902','110000','succeeded',now());
INSERT INTO app_private.source_records(id,source_id,source_key,raw_payload,source_url,content_hash,import_run_id)
VALUES('00000000-0000-4000-8000-000000000904','00000000-0000-4000-8000-000000000902','p11-synthetic','{"name":"候选眼科中心","address":"测试路 1 号","specialties":"眼科"}','https://example.test/record',repeat('d',64),'00000000-0000-4000-8000-000000000903');
INSERT INTO app_private.candidate_records(id,source_record_id,parsed_fields,normalized_name,normalized_address,administrative_code,match_status)
VALUES('00000000-0000-4000-8000-000000000905','00000000-0000-4000-8000-000000000904','{"name":"候选眼科中心","address":"测试路 1 号"}','候选眼科中心','测试路 1 号','110000','unmatched');
INSERT INTO app_private.candidate_evidence(candidate_record_id,source_record_id,field_name,evidence_value,evidence_text,evidence_type,rule_version)
VALUES('00000000-0000-4000-8000-000000000905','00000000-0000-4000-8000-000000000904','specialties','"眼科"','眼科','explicit_field_mention','p3-test-v1');

DO $$ BEGIN
  IF has_table_privilege('eye_admin_review','app_private.facilities','UPDATE') THEN RAISE EXCEPTION 'admin role must not update facilities directly'; END IF;
  IF has_table_privilege('eye_admin_review','app_private.candidate_records','UPDATE') THEN RAISE EXCEPTION 'admin role must not update candidates directly'; END IF;
  IF has_table_privilege('eye_admin_review','app_private.source_records','SELECT') THEN RAISE EXCEPTION 'admin role must not read raw source records'; END IF;
  IF NOT has_table_privilege('eye_admin_review','app_private.admin_candidate_review','SELECT') THEN RAISE EXCEPTION 'admin candidate projection is not readable'; END IF;
  IF has_function_privilege('public','app_private.admin_decide(uuid,uuid,text,uuid,text,jsonb,text)','EXECUTE') THEN RAISE EXCEPTION 'PUBLIC must not call admin decision function'; END IF;
  IF has_function_privilege('eye_public_api','app_private.admin_decide(uuid,uuid,text,uuid,text,jsonb,text)','EXECUTE') THEN RAISE EXCEPTION 'public API role must not call admin decision function'; END IF;
  IF NOT has_function_privilege('eye_admin_review','app_private.admin_decide(uuid,uuid,text,uuid,text,jsonb,text)','EXECUTE') THEN RAISE EXCEPTION 'admin role must execute decision function'; END IF;
END $$;

SET LOCAL SESSION AUTHORIZATION eye_admin_review_runtime;
SELECT app_private.admin_decide('00000000-0000-4000-8000-000000000906','00000000-0000-4000-8000-000000000907','candidate','00000000-0000-4000-8000-000000000905','CREATE_FACILITY','{"name":"候选眼科中心","address":"测试路 1 号","regionId":"00000000-0000-4000-8000-000000000901","category":"ophthalmology_center"}','通过合成审核验证创建机构');
SELECT app_private.admin_decide('00000000-0000-4000-8000-000000000906','00000000-0000-4000-8000-000000000907','candidate','00000000-0000-4000-8000-000000000905','CREATE_FACILITY','{"name":"候选眼科中心","address":"测试路 1 号","regionId":"00000000-0000-4000-8000-000000000901","category":"ophthalmology_center"}','通过合成审核验证创建机构');
RESET SESSION AUTHORIZATION;

DO $$
DECLARE facility_count integer; audit_count integer; candidate_status text; source_count integer;
BEGIN
  SELECT count(*) INTO facility_count FROM app_private.facilities WHERE name='候选眼科中心';
  SELECT count(*) INTO audit_count FROM app_private.audit_events WHERE request_id='00000000-0000-4000-8000-000000000906';
  SELECT match_status INTO candidate_status FROM app_private.candidate_records WHERE id='00000000-0000-4000-8000-000000000905';
  SELECT count(*) INTO source_count FROM app_private.source_records WHERE id='00000000-0000-4000-8000-000000000904';
  IF facility_count<>1 OR audit_count<>1 OR candidate_status<>'matched' OR source_count<>1 THEN RAISE EXCEPTION 'candidate decision/idempotency/source preservation failed'; END IF;
END $$;

DO $$
BEGIN
  INSERT INTO app_private.audit_events(entity,entity_id,action) VALUES('test','00000000-0000-4000-8000-000000000908','test');
  BEGIN
    UPDATE app_private.audit_events SET action='tampered' WHERE entity_id='00000000-0000-4000-8000-000000000908';
    RAISE EXCEPTION 'audit update was not blocked';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
END $$;
ROLLBACK;
