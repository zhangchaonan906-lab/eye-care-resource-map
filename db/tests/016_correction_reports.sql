\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE correction_facility_count_before AS SELECT count(*)::integer AS count FROM app_private.facilities;
DO $$ BEGIN
  IF has_table_privilege('eye_correction_runtime','app_private.correction_reports','INSERT')
     OR has_table_privilege('eye_correction_runtime','app_private.correction_reports','SELECT') THEN
    RAISE EXCEPTION 'submitter must not access correction table directly';
  END IF;
  IF NOT has_function_privilege('eye_correction_runtime','app_private.submit_correction_report(uuid,text,text)','EXECUTE') THEN
    RAISE EXCEPTION 'submitter cannot call the bounded correction function';
  END IF;
  IF has_function_privilege('public','app_private.submit_correction_report(uuid,text,text)','EXECUTE') THEN
    RAISE EXCEPTION 'PUBLIC must not submit correction reports';
  END IF;
  IF NOT has_table_privilege('eye_admin_review','app_private.admin_correction_review','SELECT') THEN
    RAISE EXCEPTION 'admin correction review projection is unavailable';
  END IF;
  IF NOT has_function_privilege('eye_admin_review_runtime','app_private.admin_decide_correction_report(uuid,uuid,uuid,text,text)','EXECUTE')
     OR has_function_privilege('eye_correction_runtime','app_private.admin_decide_correction_report(uuid,uuid,uuid,text,text)','EXECUTE')
     OR has_function_privilege('public','app_private.admin_decide_correction_report(uuid,uuid,uuid,text,text)','EXECUTE') THEN
    RAISE EXCEPTION 'correction disposition must be admin-only';
  END IF;
END $$;

SET SESSION AUTHORIZATION eye_correction_runtime;
SELECT app_private.submit_correction_report(NULL,'source_issue','Regression test report only') AS correction_report_id \gset
RESET SESSION AUTHORIZATION;

SET SESSION AUTHORIZATION eye_admin_review_runtime;
SELECT app_private.admin_decide_correction_report(:'correction_report_id'::uuid,'00000000-0000-4000-8000-000000000916','00000000-0000-4000-8000-000000000917','START_REVIEW','Regression review started');
SELECT app_private.admin_decide_correction_report(:'correction_report_id'::uuid,'00000000-0000-4000-8000-000000000916','00000000-0000-4000-8000-000000000917','START_REVIEW','Regression review started');
RESET SESSION AUTHORIZATION;

DO $$
DECLARE before_count integer; after_count integer;
BEGIN
  SELECT count INTO before_count FROM correction_facility_count_before;
  SELECT count(*) INTO after_count FROM app_private.correction_reports WHERE issue_type='source_issue' AND description='Regression test report only' AND status='reviewing';
  IF after_count<>1 THEN RAISE EXCEPTION 'correction must be queued and reviewed through the admin decision function'; END IF;
  IF before_count<>(SELECT count(*) FROM app_private.facilities) THEN RAISE EXCEPTION 'correction mutated canonical facilities'; END IF;
END $$;
ROLLBACK;
