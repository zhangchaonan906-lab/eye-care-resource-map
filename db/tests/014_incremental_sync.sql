\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE fixture_source uuid; manual_source uuid; pending_source uuid; suspended_source uuid;
  policy_id uuid; task_row app_private.source_sync_tasks%ROWTYPE; scheduler_now timestamptz := now();
  inserted integer; erase_source uuid; erase_run uuid; erase_record uuid; erase_new_record uuid;
BEGIN
  SELECT id INTO fixture_source FROM app_private.source_catalog
  WHERE name='Fixture Directory' AND status='approved' AND access_policy='automated_access_allowed';
  SELECT id INTO manual_source FROM app_private.source_catalog WHERE name='Fixture Blocked Directory';
  SELECT id INTO pending_source FROM app_private.source_catalog WHERE name='Fixture Pending Directory';
  SELECT id INTO suspended_source FROM app_private.source_catalog WHERE name='Fixture Suspended Directory';
  IF fixture_source IS NULL OR manual_source IS NULL OR pending_source IS NULL OR suspended_source IS NULL THEN
    RAISE EXCEPTION 'P12 test source fixture is missing';
  END IF;

  INSERT INTO app_private.source_sync_policies(source_id,region_code,adapter_key,enabled,interval_minutes,
    run_timeout_seconds,max_attempts,backoff_base_seconds,max_backoff_seconds,pause_after_failures,next_due_at)
  VALUES(fixture_source,'110000','fixture',true,60,300,3,10,60,4,scheduler_now-interval '10 days')
  RETURNING id INTO policy_id;
  INSERT INTO app_private.source_sync_policies(source_id,region_code,adapter_key,enabled,interval_minutes,next_due_at)
  VALUES(manual_source,'110000','fixture',true,60,scheduler_now-interval '1 day'),
    (pending_source,'110000','fixture',true,60,scheduler_now-interval '1 day'),
    (suspended_source,'110000','fixture',true,60,scheduler_now-interval '1 day');
  INSERT INTO app_private.source_sync_policies(source_id,region_code,adapter_key,enabled,interval_minutes,next_due_at)
  VALUES(fixture_source,'110001','fixture',false,60,scheduler_now-interval '1 day');
  INSERT INTO app_private.source_sync_policies(source_id,region_code,adapter_key,enabled,interval_minutes,
    next_due_at,paused_at,pause_reason)
  VALUES(fixture_source,'110002','fixture',true,60,scheduler_now-interval '1 day',scheduler_now,'ADMIN_PAUSED');

  SELECT app_private.enqueue_due_source_sync_tasks(scheduler_now) INTO inserted;
  IF inserted<>1 THEN RAISE EXCEPTION 'scheduler must only enqueue approved automated sources: %',inserted; END IF;
  IF (SELECT next_due_at FROM app_private.source_sync_policies WHERE id=policy_id)
     <> scheduler_now+interval '60 minutes' THEN RAISE EXCEPTION 'scheduler catch-up policy is incorrect'; END IF;
  IF app_private.enqueue_due_source_sync_tasks(scheduler_now)=1 THEN RAISE EXCEPTION 'scheduler duplicate enqueue'; END IF;

  SELECT * INTO task_row FROM app_private.claim_source_sync_task('p12-sql-worker',30,scheduler_now);
  IF task_row.status<>'running' OR task_row.attempt_count<>1 OR task_row.lease_owner<>'p12-sql-worker'
     THEN RAISE EXCEPTION 'worker failed to claim due task'; END IF;
  IF EXISTS (SELECT 1 FROM app_private.claim_source_sync_task('p12-second-worker',30,scheduler_now+interval '1 second'))
     THEN RAISE EXCEPTION 'live lease allowed a second worker claim'; END IF;
  SELECT * INTO task_row FROM app_private.claim_source_sync_task('p12-second-worker',30,scheduler_now+interval '31 seconds');
  IF task_row.id IS NULL OR task_row.attempt_count<>2 OR task_row.lease_owner<>'p12-second-worker'
     THEN RAISE EXCEPTION 'expired lease was not safely reclaimed'; END IF;

  UPDATE app_private.source_catalog SET status='suspended' WHERE id=fixture_source;
  IF EXISTS (SELECT 1 FROM app_private.claim_source_sync_task('p12-third-worker',30,scheduler_now+interval '62 seconds'))
     THEN RAISE EXCEPTION 'worker claimed a task after source suspension'; END IF;
  IF (SELECT status FROM app_private.source_sync_tasks WHERE id=task_row.id)<>'dead_letter'
     THEN RAISE EXCEPTION 'task was not isolated after source suspension'; END IF;
  IF (SELECT status FROM app_private.source_catalog WHERE id=fixture_source)<>'suspended'
     THEN RAISE EXCEPTION 'sync workflow changed source approval state'; END IF;

  IF has_table_privilege('eye_sync_worker','app_private.source_sync_tasks','UPDATE')
     OR has_table_privilege('eye_sync_worker','app_private.source_catalog','UPDATE')
     OR has_table_privilege('eye_sync_worker','app_private.source_records','SELECT') THEN
    RAISE EXCEPTION 'sync worker has direct table privileges';
  END IF;
  IF has_table_privilege('eye_admin_review','app_private.source_sync_tasks','UPDATE')
     OR has_function_privilege('eye_sync_worker','app_private.admin_enqueue_source_sync_task(uuid,uuid,uuid,text)','EXECUTE')
     OR has_function_privilege('eye_public_api','app_private.admin_set_source_sync_paused(uuid,uuid,uuid,text,boolean)','EXECUTE') THEN
    RAISE EXCEPTION 'admin/worker sync privilege boundary is too broad';
  END IF;
  IF has_function_privilege('eye_public_api','app_private.claim_source_sync_task(text,integer,timestamp with time zone)','EXECUTE')
     OR has_function_privilege('public','app_private.claim_source_sync_task(text,integer,timestamp with time zone)','EXECUTE') THEN
    RAISE EXCEPTION 'public API or PUBLIC can claim sync work';
  END IF;

  INSERT INTO app_private.source_catalog(name,url,use_basis,access_policy,status,retention_restrictions)
  VALUES('P12 erase fixture','https://fixture.invalid/p12-erase','Synthetic erasure regression',
    'manual_only','approved','delete_on_withdrawal') RETURNING id INTO erase_source;
  INSERT INTO app_private.import_runs(source_id,region_code,status,ended_at)
  VALUES(erase_source,'110000','succeeded',now()) RETURNING id INTO erase_run;
  INSERT INTO app_private.source_records(source_id,source_key,raw_payload,source_url,content_hash,import_run_id)
  VALUES(erase_source,'erase-key','{"name":"synthetic"}'::jsonb,'https://fixture.invalid/p12-erase/1',repeat('a',64),erase_run)
  RETURNING id INTO erase_record;
  INSERT INTO app_private.source_records(source_id,source_key,raw_payload,source_url,content_hash,import_run_id)
  VALUES(erase_source,'erase-key','{"name":"synthetic changed"}'::jsonb,'https://fixture.invalid/p12-erase/1',repeat('b',64),erase_run)
  RETURNING id INTO erase_new_record;
  INSERT INTO app_private.source_change_events(source_id,source_key,change_type,source_record_id,import_run_id)
  VALUES(erase_source,'erase-key','NEW',erase_record,erase_run);
  INSERT INTO app_private.source_change_events(source_id,source_key,change_type,previous_source_record_id,source_record_id,import_run_id)
  VALUES(erase_source,'erase-key','CHANGED',erase_record,erase_new_record,erase_run);
  UPDATE app_private.source_catalog SET status='suspended' WHERE id=erase_source;
  IF app_private.erase_withdrawn_source_records(erase_source)<>2 THEN
    RAISE EXCEPTION 'source erasure did not remove linked immutable snapshot';
  END IF;
  IF EXISTS (SELECT 1 FROM app_private.source_change_events WHERE source_id=erase_source) THEN
    RAISE EXCEPTION 'source erasure left dangling change events';
  END IF;
END;
$$;

DO $$
DECLARE source_a uuid; source_b uuid; policy_a uuid; policy_b uuid; task_a uuid; task_b uuid;
  task_row app_private.source_sync_tasks%ROWTYPE; run_b uuid; base_now timestamptz:=now(); result_status text;
BEGIN
  INSERT INTO app_private.source_catalog(name,url,use_basis,permitted_fields,access_policy,status,reviewed_at)
  VALUES('P12 failure isolation A','https://fixture.invalid/failure-a','Synthetic test only',ARRAY['name'],
    'automated_access_allowed','approved',base_now) RETURNING id INTO source_a;
  INSERT INTO app_private.source_catalog(name,url,use_basis,permitted_fields,access_policy,status,reviewed_at)
  VALUES('P12 failure isolation B','https://fixture.invalid/failure-b','Synthetic test only',ARRAY['name'],
    'automated_access_allowed','approved',base_now) RETURNING id INTO source_b;
  INSERT INTO app_private.source_sync_policies(source_id,region_code,adapter_key,enabled,interval_minutes,
    max_attempts,backoff_base_seconds,max_backoff_seconds,next_due_at)
  VALUES(source_a,'110000','fixture',true,60,3,10,60,base_now-interval '1 minute') RETURNING id INTO policy_a;
  INSERT INTO app_private.source_sync_policies(source_id,region_code,adapter_key,enabled,interval_minutes,
    max_attempts,backoff_base_seconds,max_backoff_seconds,next_due_at)
  VALUES(source_b,'440000','fixture',true,60,3,10,60,base_now-interval '1 minute') RETURNING id INTO policy_b;
  IF app_private.enqueue_due_source_sync_tasks(base_now)<>2 THEN RAISE EXCEPTION 'both isolated test sources should enqueue'; END IF;
  SELECT id INTO task_a FROM app_private.source_sync_tasks WHERE source_sync_policy_id=policy_a;
  SELECT id INTO task_b FROM app_private.source_sync_tasks WHERE source_sync_policy_id=policy_b;
  SELECT * INTO task_row FROM app_private.claim_source_sync_task('p12-worker-a',30,base_now);
  IF task_row.id IS NULL THEN RAISE EXCEPTION 'source A was not claimed'; END IF;
  IF task_row.id=task_b THEN task_a:=task_row.id; task_b:=(SELECT id FROM app_private.source_sync_tasks WHERE source_sync_policy_id=policy_a);
  ELSE task_a:=task_row.id; END IF;
  SELECT source_id INTO source_b FROM app_private.source_sync_tasks WHERE id=task_b;
  result_status:=app_private.retry_source_sync_task(task_a,'p12-worker-a','NETWORK_TIMEOUT',
    'Synthetic timeout',true,base_now);
  IF result_status<>'retry_wait' OR
    (SELECT not_before FROM app_private.source_sync_tasks WHERE id=task_a)<>base_now+interval '10 seconds' THEN
    RAISE EXCEPTION 'first retry must persist capped exponential backoff';
  END IF;
  SELECT * INTO task_row FROM app_private.claim_source_sync_task('p12-worker-b',30,base_now+interval '1 second')
    WHERE id=task_b;
  IF task_row.id IS NULL THEN RAISE EXCEPTION 'source B was blocked by source A retry'; END IF;
  INSERT INTO app_private.import_runs(source_id,region_code,status,ended_at)
  VALUES(source_b,'440000','succeeded',base_now) RETURNING id INTO run_b;
  IF NOT app_private.record_source_sync_collection(task_b,'p12-worker-b',run_b,'{"new":0}'::jsonb,base_now+interval '1 second') THEN
    RAISE EXCEPTION 'source B collection stage did not persist';
  END IF;
  IF NOT app_private.complete_source_sync_task(task_b,'p12-worker-b','{"etl":{"errors":0}}'::jsonb,base_now+interval '2 seconds') THEN
    RAISE EXCEPTION 'source B could not complete while source A retries';
  END IF;
  IF (SELECT status FROM app_private.source_sync_tasks WHERE id=task_b)<>'succeeded' THEN
    RAISE EXCEPTION 'source B did not finish independently';
  END IF;
  SELECT * INTO task_row FROM app_private.claim_source_sync_task('p12-worker-a-retry',30,base_now+interval '11 seconds');
  IF task_row.id<>task_a OR task_row.attempt_count<>2 THEN RAISE EXCEPTION 'retry task was not claimable after not_before'; END IF;
  result_status:=app_private.retry_source_sync_task(task_a,'p12-worker-a-retry','SCHEMA_CHANGED',
    'Synthetic schema drift',false,base_now+interval '11 seconds');
  IF result_status<>'dead_letter' OR
    (SELECT pause_reason FROM app_private.source_sync_policies WHERE id=(SELECT source_sync_policy_id FROM app_private.source_sync_tasks WHERE id=task_a))<>'SCHEMA_CHANGED' OR
    NOT EXISTS (SELECT 1 FROM app_private.source_sync_alerts WHERE task_id=task_a AND code='SCHEMA_CHANGED') THEN
    RAISE EXCEPTION 'severe source failure must pause schedule and persist an alert';
  END IF;
  IF (SELECT status FROM app_private.source_catalog WHERE id=(SELECT source_id FROM app_private.source_sync_tasks WHERE id=task_a))<>'approved' THEN
    RAISE EXCEPTION 'sync failure changed source approval state';
  END IF;
END;
$$;

DO $$
DECLARE p_source uuid; actor uuid:='00000000-0000-4000-8000-000000009014'; req uuid:='00000000-0000-4000-8000-000000009015';
  first_result jsonb; replay_result jsonb; manual_id uuid;
BEGIN
  SELECT id INTO p_source FROM app_private.source_catalog WHERE name='P12 failure isolation B';
  first_result:=app_private.admin_enqueue_source_sync_task(p_source,actor,req,'Controlled sync test');
  replay_result:=app_private.admin_enqueue_source_sync_task(p_source,actor,req,'Controlled sync test');
  IF first_result<>replay_result OR
    (SELECT count(*) FROM app_private.source_sync_tasks t WHERE t.request_id=req)<>1 OR
    (SELECT count(*) FROM app_private.audit_events a WHERE a.request_id=req AND a.action='RUN_NOW')<>1 THEN
    RAISE EXCEPTION 'RUN_NOW replay must return one audited task';
  END IF;
  PERFORM app_private.admin_set_source_sync_paused(p_source,actor,'00000000-0000-4000-8000-000000009016',
    'Pause sync test reason',true);
  IF (SELECT p.pause_reason FROM app_private.source_sync_policies p WHERE p.source_id=p_source)<>'ADMIN_PAUSED' THEN
    RAISE EXCEPTION 'admin pause did not pause only the schedule';
  END IF;
  PERFORM app_private.admin_set_source_sync_paused(p_source,actor,'00000000-0000-4000-8000-000000009017',
    'Resume sync test reason',false);
  IF (SELECT p.paused_at FROM app_private.source_sync_policies p WHERE p.source_id=p_source) IS NOT NULL THEN
    RAISE EXCEPTION 'admin resume did not clear schedule pause';
  END IF;
  IF (SELECT s.status FROM app_private.source_catalog s WHERE s.id=p_source)<>'approved' THEN
    RAISE EXCEPTION 'admin schedule actions changed source approval';
  END IF;
  SELECT id INTO manual_id FROM app_private.source_catalog WHERE name='Fixture Blocked Directory';
  BEGIN
    PERFORM app_private.admin_enqueue_source_sync_task(manual_id,actor,'00000000-0000-4000-8000-000000009018',
      'Manual source block test');
    RAISE EXCEPTION 'manual-only RUN_NOW was unexpectedly accepted';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM NOT LIKE '%MANUAL_FILE_REQUIRED%' THEN RAISE; END IF;
  END;
END;
$$;

ROLLBACK;
