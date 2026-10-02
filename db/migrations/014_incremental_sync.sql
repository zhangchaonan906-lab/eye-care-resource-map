\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_sync_worker') THEN
    CREATE ROLE eye_sync_worker NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

CREATE TABLE app_private.source_sync_policies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id) ON DELETE CASCADE,
  region_code text NOT NULL CHECK (region_code ~ '^[0-9]{6}$'),
  adapter_key text NOT NULL CHECK (adapter_key ~ '^[a-z][a-z0-9_-]{0,63}$'),
  enabled boolean NOT NULL DEFAULT false,
  interval_minutes integer NOT NULL CHECK (interval_minutes BETWEEN 60 AND 525600),
  run_timeout_seconds integer NOT NULL DEFAULT 3600 CHECK (run_timeout_seconds BETWEEN 30 AND 86400),
  max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 5),
  backoff_base_seconds integer NOT NULL DEFAULT 30 CHECK (backoff_base_seconds BETWEEN 1 AND 3600),
  max_backoff_seconds integer NOT NULL DEFAULT 3600 CHECK (max_backoff_seconds BETWEEN backoff_base_seconds AND 86400),
  pause_after_failures integer NOT NULL DEFAULT 5 CHECK (pause_after_failures BETWEEN 1 AND 20),
  consecutive_failures integer NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
  next_due_at timestamptz NOT NULL DEFAULT now(),
  paused_at timestamptz,
  pause_reason text CHECK (pause_reason IS NULL OR pause_reason IN (
    'ADMIN_PAUSED','CONSECUTIVE_FAILURES','SCHEMA_CHANGED','POLICY_BLOCKED',
    'ACCESS_FORBIDDEN','ADAPTER_CONFIG_INVALID'
  )),
  last_success_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, region_code),
  CHECK ((paused_at IS NULL) = (pause_reason IS NULL))
);

CREATE TABLE app_private.source_sync_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_sync_policy_id uuid NOT NULL REFERENCES app_private.source_sync_policies(id) ON DELETE RESTRICT,
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id) ON DELETE RESTRICT,
  region_code text NOT NULL CHECK (region_code ~ '^[0-9]{6}$'),
  adapter_key text NOT NULL CHECK (adapter_key ~ '^[a-z][a-z0-9_-]{0,63}$'),
  trigger text NOT NULL CHECK (trigger IN ('scheduled','manual')),
  scheduled_for timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('queued','running','retry_wait','succeeded','dead_letter','cancelled')),
  stage text NOT NULL CHECK (stage IN ('collect','etl','complete')),
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  not_before timestamptz NOT NULL,
  run_timeout_seconds integer NOT NULL CHECK (run_timeout_seconds BETWEEN 30 AND 86400),
  max_attempts integer NOT NULL CHECK (max_attempts BETWEEN 1 AND 5),
  backoff_base_seconds integer NOT NULL CHECK (backoff_base_seconds BETWEEN 1 AND 3600),
  max_backoff_seconds integer NOT NULL CHECK (max_backoff_seconds BETWEEN backoff_base_seconds AND 86400),
  pause_after_failures integer NOT NULL CHECK (pause_after_failures BETWEEN 1 AND 20),
  lease_owner text,
  lease_expires_at timestamptz,
  import_run_id uuid REFERENCES app_private.import_runs(id) ON DELETE SET NULL,
  counts jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(counts) = 'object'),
  last_error_code text,
  last_error_summary text CHECK (last_error_summary IS NULL OR length(last_error_summary) <= 500),
  request_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'running') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)),
  CHECK (status <> 'succeeded' OR (stage = 'complete' AND finished_at IS NOT NULL)),
  CHECK (status NOT IN ('dead_letter','cancelled') OR finished_at IS NOT NULL)
);
CREATE UNIQUE INDEX source_sync_tasks_one_active_uq
  ON app_private.source_sync_tasks(source_id, region_code)
  WHERE status IN ('queued','running','retry_wait');
CREATE UNIQUE INDEX source_sync_tasks_request_id_uq
  ON app_private.source_sync_tasks(request_id) WHERE request_id IS NOT NULL;
CREATE INDEX source_sync_tasks_claim_idx
  ON app_private.source_sync_tasks(status, not_before, created_at)
  WHERE status IN ('queued','retry_wait','running');

CREATE TABLE app_private.source_change_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id) ON DELETE CASCADE,
  source_key text NOT NULL,
  change_type text NOT NULL CHECK (change_type IN ('NEW','CHANGED')),
  previous_source_record_id uuid REFERENCES app_private.source_records(id) ON DELETE CASCADE,
  source_record_id uuid NOT NULL UNIQUE REFERENCES app_private.source_records(id) ON DELETE CASCADE,
  import_run_id uuid NOT NULL REFERENCES app_private.import_runs(id) ON DELETE CASCADE,
  changed_paths text[] NOT NULL DEFAULT '{}',
  diff_truncated boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (cardinality(changed_paths) <= 100),
  CHECK ((change_type = 'NEW' AND previous_source_record_id IS NULL) OR
         (change_type = 'CHANGED' AND previous_source_record_id IS NOT NULL))
);
CREATE INDEX source_change_events_source_created_idx
  ON app_private.source_change_events(source_id, created_at DESC);

CREATE TABLE app_private.source_sync_alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id) ON DELETE CASCADE,
  task_id uuid REFERENCES app_private.source_sync_tasks(id) ON DELETE SET NULL,
  code text NOT NULL CHECK (code IN (
    'TASK_TIMEOUT','NETWORK_TIMEOUT','HTTP_429','HTTP_5XX','DATABASE_TRANSIENT',
    'COLLECTION_FAILED','ETL_FAILED','WORKER_CRASH','SCHEMA_CHANGED','POLICY_BLOCKED',
    'ACCESS_FORBIDDEN','ADAPTER_CONFIG_INVALID','CONSECUTIVE_FAILURES','MAX_ATTEMPTS'
  )),
  severity text NOT NULL CHECK (severity IN ('warning','error','critical')),
  message text NOT NULL CHECK (length(message) BETWEEN 1 AND 500),
  opened_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);
CREATE INDEX source_sync_alerts_open_idx ON app_private.source_sync_alerts(source_id, opened_at DESC)
  WHERE resolved_at IS NULL;

CREATE OR REPLACE FUNCTION app_private.enqueue_due_source_sync_tasks(p_now timestamptz DEFAULT now())
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE policy_row record; task_id uuid; queued integer := 0;
BEGIN
  FOR policy_row IN
    SELECT p.* FROM app_private.source_sync_policies p
    JOIN app_private.source_catalog s ON s.id=p.source_id
    WHERE p.enabled AND p.paused_at IS NULL AND p.next_due_at <= p_now
      AND s.status='approved' AND s.access_policy='automated_access_allowed'
    ORDER BY p.next_due_at, p.id
    FOR UPDATE OF p SKIP LOCKED
  LOOP
    INSERT INTO app_private.source_sync_tasks (
      source_sync_policy_id,source_id,region_code,adapter_key,trigger,scheduled_for,status,stage,
      not_before,run_timeout_seconds,max_attempts,backoff_base_seconds,max_backoff_seconds,pause_after_failures
    ) VALUES (
      policy_row.id,policy_row.source_id,policy_row.region_code,policy_row.adapter_key,'scheduled',
      p_now,'queued','collect',p_now,policy_row.run_timeout_seconds,policy_row.max_attempts,
      policy_row.backoff_base_seconds,policy_row.max_backoff_seconds,policy_row.pause_after_failures
    ) ON CONFLICT DO NOTHING RETURNING id INTO task_id;
    IF task_id IS NOT NULL THEN
      UPDATE app_private.source_sync_policies
      SET next_due_at=p_now + make_interval(mins => policy_row.interval_minutes),updated_at=p_now
      WHERE id=policy_row.id;
      queued := queued + 1;
    END IF;
    task_id := NULL;
  END LOOP;
  RETURN queued;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.admin_enqueue_source_sync_task(
  p_source_id uuid, p_actor_id uuid, p_request_id uuid, p_reason text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE policy_row record; saved app_private.admin_idempotency%ROWTYPE; result_value jsonb; new_task_id uuid;
BEGIN
  IF p_actor_id IS NULL OR p_request_id IS NULL OR length(trim(p_reason)) NOT BETWEEN 5 AND 500 THEN
    RAISE EXCEPTION 'invalid sync decision request' USING ERRCODE='22023';
  END IF;
  INSERT INTO app_private.admin_idempotency(request_id,actor_id,entity,entity_id,action,result)
  VALUES(p_request_id,p_actor_id,'sync_policy',p_source_id,'RUN_NOW','{}'::jsonb)
  ON CONFLICT (request_id) DO NOTHING;
  SELECT * INTO saved FROM app_private.admin_idempotency WHERE request_id=p_request_id FOR UPDATE;
  IF saved.actor_id<>p_actor_id OR saved.entity<>'sync_policy' OR saved.entity_id<>p_source_id OR saved.action<>'RUN_NOW' THEN
    RAISE EXCEPTION 'idempotency key already used for another action' USING ERRCODE='23505';
  END IF;
  IF saved.result <> '{}'::jsonb THEN RETURN saved.result; END IF;
  SELECT p.*,s.status AS source_status,s.access_policy INTO policy_row
  FROM app_private.source_sync_policies p JOIN app_private.source_catalog s ON s.id=p.source_id
  WHERE p.source_id=p_source_id ORDER BY p.region_code LIMIT 1 FOR UPDATE OF p;
  IF NOT FOUND THEN RAISE EXCEPTION 'sync policy not found' USING ERRCODE='P0002'; END IF;
  IF policy_row.access_policy='manual_only' THEN
    RAISE EXCEPTION 'MANUAL_FILE_REQUIRED' USING ERRCODE='23514';
  END IF;
  IF policy_row.source_status<>'approved' OR policy_row.access_policy<>'automated_access_allowed' THEN
    RAISE EXCEPTION 'POLICY_BLOCKED' USING ERRCODE='23514';
  END IF;
  INSERT INTO app_private.source_sync_tasks (
    source_sync_policy_id,source_id,region_code,adapter_key,trigger,scheduled_for,status,stage,
    not_before,run_timeout_seconds,max_attempts,backoff_base_seconds,max_backoff_seconds,pause_after_failures,request_id
  ) VALUES (
    policy_row.id,policy_row.source_id,policy_row.region_code,policy_row.adapter_key,'manual',now(),
    'queued','collect',now(),policy_row.run_timeout_seconds,policy_row.max_attempts,
    policy_row.backoff_base_seconds,policy_row.max_backoff_seconds,policy_row.pause_after_failures,p_request_id
  ) ON CONFLICT DO NOTHING RETURNING id INTO new_task_id;
  IF new_task_id IS NULL THEN RAISE EXCEPTION 'active sync task already exists' USING ERRCODE='23505'; END IF;
  result_value := jsonb_build_object('taskId',new_task_id,'status','queued');
  UPDATE app_private.admin_idempotency SET result=result_value WHERE request_id=p_request_id;
  INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,after_value)
  VALUES(p_actor_id,'sync_policy',p_source_id,'RUN_NOW',trim(p_reason),p_request_id,result_value);
  RETURN result_value;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.admin_set_source_sync_paused(
  p_source_id uuid, p_actor_id uuid, p_request_id uuid, p_reason text, p_paused boolean
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE saved app_private.admin_idempotency%ROWTYPE; result_value jsonb; before_state jsonb; policy_id uuid;
BEGIN
  IF p_actor_id IS NULL OR p_request_id IS NULL OR length(trim(p_reason)) NOT BETWEEN 5 AND 500 THEN
    RAISE EXCEPTION 'invalid sync decision request' USING ERRCODE='22023';
  END IF;
  INSERT INTO app_private.admin_idempotency(request_id,actor_id,entity,entity_id,action,result)
  VALUES(p_request_id,p_actor_id,'sync_policy',p_source_id,CASE WHEN p_paused THEN 'PAUSE_SYNC' ELSE 'RESUME_SYNC' END,'{}'::jsonb)
  ON CONFLICT (request_id) DO NOTHING;
  SELECT * INTO saved FROM app_private.admin_idempotency WHERE request_id=p_request_id FOR UPDATE;
  IF saved.actor_id<>p_actor_id OR saved.entity<>'sync_policy' OR saved.entity_id<>p_source_id
     OR saved.action<>(CASE WHEN p_paused THEN 'PAUSE_SYNC' ELSE 'RESUME_SYNC' END) THEN
    RAISE EXCEPTION 'idempotency key already used for another action' USING ERRCODE='23505';
  END IF;
  IF saved.result <> '{}'::jsonb THEN RETURN saved.result; END IF;
  SELECT id,to_jsonb(p) INTO policy_id,before_state FROM app_private.source_sync_policies p
  WHERE source_id=p_source_id ORDER BY region_code LIMIT 1 FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'sync policy not found' USING ERRCODE='P0002'; END IF;
  UPDATE app_private.source_sync_policies SET
    paused_at=CASE WHEN p_paused THEN now() ELSE NULL END,
    pause_reason=CASE WHEN p_paused THEN 'ADMIN_PAUSED' ELSE NULL END,
    updated_at=now()
  WHERE id=policy_id;
  SELECT jsonb_build_object('sourceId',p_source_id,'paused',p_paused,'status','updated') INTO result_value;
  UPDATE app_private.admin_idempotency SET result=result_value WHERE request_id=p_request_id;
  INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,before_value,after_value)
  VALUES(p_actor_id,'sync_policy',p_source_id,CASE WHEN p_paused THEN 'PAUSE_SYNC' ELSE 'RESUME_SYNC' END,
    trim(p_reason),p_request_id,before_state,(SELECT to_jsonb(p) FROM app_private.source_sync_policies p WHERE p.id=policy_id));
  RETURN result_value;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.claim_source_sync_task(
  p_worker_id text, p_lease_seconds integer, p_now timestamptz DEFAULT now()
) RETURNS SETOF app_private.source_sync_tasks LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE task_row app_private.source_sync_tasks%ROWTYPE; source_ok boolean;
BEGIN
  IF p_worker_id IS NULL OR length(trim(p_worker_id)) NOT BETWEEN 1 AND 128
     OR p_lease_seconds NOT BETWEEN 30 AND 3600 THEN
    RAISE EXCEPTION 'invalid worker claim parameters' USING ERRCODE='22023';
  END IF;
  FOR task_row IN
    SELECT t.* FROM app_private.source_sync_tasks t
    JOIN app_private.source_sync_policies p ON p.id=t.source_sync_policy_id
    WHERE ((t.status IN ('queued','retry_wait') AND t.not_before<=p_now)
       OR (t.status='running' AND t.lease_expires_at<=p_now))
      AND p.enabled AND p.paused_at IS NULL
    ORDER BY t.not_before,t.created_at,t.id
    FOR UPDATE OF t SKIP LOCKED
  LOOP
    SELECT (s.status='approved' AND s.access_policy='automated_access_allowed') INTO source_ok
    FROM app_private.source_catalog s WHERE s.id=task_row.source_id;
    IF source_ok IS DISTINCT FROM true THEN
      UPDATE app_private.source_sync_tasks SET status='dead_letter',stage='complete',
        last_error_code='POLICY_BLOCKED',last_error_summary='Source policy no longer permits automated access',
        finished_at=p_now,lease_owner=NULL,lease_expires_at=NULL,updated_at=p_now WHERE id=task_row.id;
      INSERT INTO app_private.source_sync_alerts(source_id,task_id,code,severity,message)
        VALUES(task_row.source_id,task_row.id,'POLICY_BLOCKED','critical','Source policy no longer permits automated access');
      CONTINUE;
    END IF;
    IF task_row.attempt_count>=task_row.max_attempts THEN
      UPDATE app_private.source_sync_tasks SET status='dead_letter',stage='complete',
        last_error_code='WORKER_CRASH',last_error_summary='Worker lease expired after maximum attempts',
        finished_at=p_now,lease_owner=NULL,lease_expires_at=NULL,updated_at=p_now WHERE id=task_row.id;
      INSERT INTO app_private.source_sync_alerts(source_id,task_id,code,severity,message)
        VALUES(task_row.source_id,task_row.id,'MAX_ATTEMPTS','critical','Worker lease expired after maximum attempts');
      CONTINUE;
    END IF;
    UPDATE app_private.source_sync_tasks SET status='running',attempt_count=attempt_count+1,
      lease_owner=trim(p_worker_id),lease_expires_at=p_now+make_interval(secs=>p_lease_seconds),
      started_at=COALESCE(started_at,p_now),updated_at=p_now
    WHERE id=task_row.id RETURNING * INTO task_row;
    RETURN NEXT task_row;
    RETURN;
  END LOOP;
  RETURN;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.heartbeat_source_sync_task(
  p_task_id uuid,p_worker_id text,p_lease_seconds integer,p_now timestamptz DEFAULT now()
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
BEGIN
  UPDATE app_private.source_sync_tasks SET lease_expires_at=p_now+make_interval(secs=>p_lease_seconds),updated_at=p_now
  WHERE id=p_task_id AND status='running' AND lease_owner=p_worker_id AND lease_expires_at>p_now
    AND p_lease_seconds BETWEEN 30 AND 3600;
  RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.approved_sync_source_descriptor(p_source_id uuid)
RETURNS TABLE(source_id uuid,source_name text,catalog_url text,access_policy text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
  SELECT s.id,s.name,s.url,s.access_policy FROM app_private.source_catalog s
  WHERE s.id=p_source_id AND s.status='approved' AND s.access_policy='automated_access_allowed'
$$;

CREATE OR REPLACE FUNCTION app_private.record_source_sync_collection(
  p_task_id uuid,p_worker_id text,p_import_run_id uuid,p_counts jsonb,p_now timestamptz DEFAULT now()
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
BEGIN
  UPDATE app_private.source_sync_tasks t SET stage='etl',import_run_id=p_import_run_id,
    counts=COALESCE(p_counts,'{}'::jsonb),updated_at=p_now
  WHERE t.id=p_task_id AND t.status='running' AND t.stage='collect' AND t.lease_owner=p_worker_id
    AND t.lease_expires_at>p_now AND EXISTS (
      SELECT 1 FROM app_private.import_runs ir WHERE ir.id=p_import_run_id AND ir.source_id=t.source_id
        AND ir.region_code=t.region_code AND ir.status='succeeded'
    );
  RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.retry_source_sync_task(
  p_task_id uuid,p_worker_id text,p_error_code text,p_safe_summary text,p_retryable boolean,
  p_now timestamptz DEFAULT now()
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE t app_private.source_sync_tasks%ROWTYPE; attempt_delay integer; failures integer;
  severe boolean; should_pause boolean; policy_pause_reason text;
BEGIN
  SELECT * INTO t FROM app_private.source_sync_tasks WHERE id=p_task_id AND status='running'
    AND lease_owner=p_worker_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'sync task lease conflict' USING ERRCODE='40001'; END IF;
  IF p_error_code NOT IN ('TASK_TIMEOUT','NETWORK_TIMEOUT','HTTP_429','HTTP_5XX','DATABASE_TRANSIENT',
    'COLLECTION_FAILED','ETL_FAILED','WORKER_CRASH','SCHEMA_CHANGED','POLICY_BLOCKED',
    'ACCESS_FORBIDDEN','ADAPTER_CONFIG_INVALID') OR p_safe_summary IS NULL
    OR length(p_safe_summary)>500 THEN RAISE EXCEPTION 'invalid task failure classification' USING ERRCODE='22023'; END IF;
  UPDATE app_private.source_sync_policies SET consecutive_failures=consecutive_failures+1,updated_at=p_now
    WHERE id=t.source_sync_policy_id RETURNING consecutive_failures INTO failures;
  severe := p_error_code IN ('SCHEMA_CHANGED','POLICY_BLOCKED','ACCESS_FORBIDDEN','ADAPTER_CONFIG_INVALID');
  should_pause := severe OR failures>=t.pause_after_failures;
  policy_pause_reason := CASE p_error_code WHEN 'SCHEMA_CHANGED' THEN 'SCHEMA_CHANGED'
    WHEN 'POLICY_BLOCKED' THEN 'POLICY_BLOCKED' WHEN 'ACCESS_FORBIDDEN' THEN 'ACCESS_FORBIDDEN'
    WHEN 'ADAPTER_CONFIG_INVALID' THEN 'ADAPTER_CONFIG_INVALID'
    WHEN 'CONSECUTIVE_FAILURES' THEN 'CONSECUTIVE_FAILURES' ELSE 'CONSECUTIVE_FAILURES' END;
  IF should_pause THEN
    UPDATE app_private.source_sync_policies SET paused_at=COALESCE(paused_at,p_now),
      pause_reason=COALESCE(pause_reason,policy_pause_reason),updated_at=p_now WHERE id=t.source_sync_policy_id;
  END IF;
  IF p_retryable AND NOT should_pause AND t.attempt_count<t.max_attempts THEN
    attempt_delay := LEAST(t.max_backoff_seconds,
      t.backoff_base_seconds * power(2,GREATEST(t.attempt_count-1,0))::integer);
    UPDATE app_private.source_sync_tasks SET status='retry_wait',not_before=p_now+make_interval(secs=>attempt_delay),
      last_error_code=p_error_code,last_error_summary=p_safe_summary,lease_owner=NULL,lease_expires_at=NULL,updated_at=p_now
      WHERE id=t.id;
    IF should_pause THEN NULL; END IF;
    IF failures>=t.pause_after_failures THEN
      INSERT INTO app_private.source_sync_alerts(source_id,task_id,code,severity,message)
        VALUES(t.source_id,t.id,'CONSECUTIVE_FAILURES','critical','Sync paused after consecutive failures');
    END IF;
    RETURN 'retry_wait';
  END IF;
  UPDATE app_private.source_sync_tasks SET status='dead_letter',stage='complete',finished_at=p_now,
    last_error_code=p_error_code,last_error_summary=p_safe_summary,lease_owner=NULL,lease_expires_at=NULL,updated_at=p_now
    WHERE id=t.id;
  INSERT INTO app_private.source_sync_alerts(source_id,task_id,code,severity,message)
    VALUES(t.source_id,t.id,CASE WHEN t.attempt_count>=t.max_attempts THEN 'MAX_ATTEMPTS' ELSE p_error_code END,
      CASE WHEN severe OR should_pause THEN 'critical' ELSE 'error' END,p_safe_summary);
  IF failures>=t.pause_after_failures AND NOT severe THEN
    INSERT INTO app_private.source_sync_alerts(source_id,task_id,code,severity,message)
      VALUES(t.source_id,t.id,'CONSECUTIVE_FAILURES','critical','Sync paused after consecutive failures');
  END IF;
  RETURN 'dead_letter';
END;
$$;

CREATE OR REPLACE FUNCTION app_private.complete_source_sync_task(
  p_task_id uuid,p_worker_id text,p_counts jsonb,p_now timestamptz DEFAULT now()
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE t app_private.source_sync_tasks%ROWTYPE;
BEGIN
  SELECT * INTO t FROM app_private.source_sync_tasks WHERE id=p_task_id AND status='running'
    AND stage='etl' AND lease_owner=p_worker_id FOR UPDATE;
  IF NOT FOUND OR t.lease_expires_at<=p_now THEN RETURN false; END IF;
  IF NOT EXISTS (SELECT 1 FROM app_private.import_runs WHERE id=t.import_run_id AND status='succeeded') THEN
    RAISE EXCEPTION 'sync task has no successful import run' USING ERRCODE='23514';
  END IF;
  UPDATE app_private.source_sync_tasks SET status='succeeded',stage='complete',counts=COALESCE(p_counts,'{}'::jsonb),
    finished_at=p_now,lease_owner=NULL,lease_expires_at=NULL,updated_at=p_now WHERE id=t.id;
  UPDATE app_private.source_sync_policies SET consecutive_failures=0,last_success_at=p_now,updated_at=p_now
    WHERE id=t.source_sync_policy_id;
  UPDATE app_private.source_sync_alerts SET resolved_at=p_now
  WHERE source_id=t.source_id AND resolved_at IS NULL
    AND code IN ('CONSECUTIVE_FAILURES','NETWORK_TIMEOUT','HTTP_429','HTTP_5XX','DATABASE_TRANSIENT',
      'TASK_TIMEOUT','COLLECTION_FAILED','ETL_FAILED','WORKER_CRASH','MAX_ATTEMPTS');
  RETURN true;
END;
$$;

CREATE VIEW app_private.admin_sync_policy_review AS
SELECT p.id,p.source_id,s.name AS source_name,s.status AS source_status,s.access_policy,p.region_code,
  p.adapter_key,p.enabled,p.interval_minutes,p.run_timeout_seconds,p.next_due_at,p.paused_at,p.pause_reason,
  p.consecutive_failures,p.pause_after_failures,p.last_success_at,p.updated_at,
  latest.status AS latest_task_status,latest.attempt_count AS latest_task_attempt,
  latest.stage AS latest_task_stage,latest.last_error_code AS latest_error_code,
  latest.last_error_summary AS latest_safe_error,COALESCE(alerts.open_alerts,0)::integer AS open_alerts
FROM app_private.source_sync_policies p JOIN app_private.source_catalog s ON s.id=p.source_id
LEFT JOIN LATERAL (
  SELECT t.status,t.attempt_count,t.stage,t.last_error_code,t.last_error_summary
  FROM app_private.source_sync_tasks t WHERE t.source_sync_policy_id=p.id
  ORDER BY t.created_at DESC,t.id DESC LIMIT 1
) latest ON true
LEFT JOIN LATERAL (
  SELECT count(*) AS open_alerts FROM app_private.source_sync_alerts a
  WHERE a.source_id=p.source_id AND a.resolved_at IS NULL
) alerts ON true;
CREATE VIEW app_private.admin_sync_task_review AS
SELECT t.id,t.source_sync_policy_id,t.source_id,s.name AS source_name,t.region_code,t.adapter_key,t.trigger,
  t.scheduled_for,t.status,t.stage,t.attempt_count,t.not_before,t.lease_expires_at,t.import_run_id,t.counts,
  t.last_error_code,t.last_error_summary,t.created_at,t.started_at,t.finished_at,t.updated_at
FROM app_private.source_sync_tasks t JOIN app_private.source_catalog s ON s.id=t.source_id;
CREATE VIEW app_private.admin_sync_alert_review AS
SELECT a.id,a.source_id,s.name AS source_name,a.task_id,a.code,a.severity,a.message,a.opened_at,a.resolved_at
FROM app_private.source_sync_alerts a JOIN app_private.source_catalog s ON s.id=a.source_id;

GRANT USAGE ON SCHEMA app_private TO eye_sync_worker, eye_admin_review;
GRANT SELECT,INSERT ON app_private.source_change_events TO eye_collector;
GRANT EXECUTE ON FUNCTION app_private.enqueue_due_source_sync_tasks(timestamptz),
  app_private.approved_sync_source_descriptor(uuid),
  app_private.claim_source_sync_task(text,integer,timestamptz),
  app_private.heartbeat_source_sync_task(uuid,text,integer,timestamptz),
  app_private.record_source_sync_collection(uuid,text,uuid,jsonb,timestamptz),
  app_private.retry_source_sync_task(uuid,text,text,text,boolean,timestamptz),
  app_private.complete_source_sync_task(uuid,text,jsonb,timestamptz)
  TO eye_sync_worker;
GRANT SELECT ON app_private.admin_sync_policy_review,app_private.admin_sync_task_review,
  app_private.admin_sync_alert_review TO eye_admin_review;
GRANT EXECUTE ON FUNCTION app_private.admin_enqueue_source_sync_task(uuid,uuid,uuid,text),
  app_private.admin_set_source_sync_paused(uuid,uuid,uuid,text,boolean) TO eye_admin_review;
REVOKE ALL ON app_private.source_sync_policies,app_private.source_sync_tasks,
  app_private.source_change_events,app_private.source_sync_alerts FROM PUBLIC,eye_public_api,
  eye_sync_worker,eye_admin_review;
REVOKE ALL ON FUNCTION app_private.enqueue_due_source_sync_tasks(timestamptz),
  app_private.approved_sync_source_descriptor(uuid),
  app_private.admin_enqueue_source_sync_task(uuid,uuid,uuid,text),
  app_private.admin_set_source_sync_paused(uuid,uuid,uuid,text,boolean),
  app_private.claim_source_sync_task(text,integer,timestamptz),
  app_private.heartbeat_source_sync_task(uuid,text,integer,timestamptz),
  app_private.record_source_sync_collection(uuid,text,uuid,jsonb,timestamptz),
  app_private.retry_source_sync_task(uuid,text,text,text,boolean,timestamptz),
  app_private.complete_source_sync_task(uuid,text,jsonb,timestamptz) FROM PUBLIC,eye_public_api;
GRANT EXECUTE ON FUNCTION app_private.enqueue_due_source_sync_tasks(timestamptz),
  app_private.approved_sync_source_descriptor(uuid),
  app_private.claim_source_sync_task(text,integer,timestamptz),
  app_private.heartbeat_source_sync_task(uuid,text,integer,timestamptz),
  app_private.record_source_sync_collection(uuid,text,uuid,jsonb,timestamptz),
  app_private.retry_source_sync_task(uuid,text,text,text,boolean,timestamptz),
  app_private.complete_source_sync_task(uuid,text,jsonb,timestamptz) TO eye_sync_worker;
GRANT EXECUTE ON FUNCTION app_private.admin_enqueue_source_sync_task(uuid,uuid,uuid,text),
  app_private.admin_set_source_sync_paused(uuid,uuid,uuid,text,boolean) TO eye_admin_review;

COMMIT;
