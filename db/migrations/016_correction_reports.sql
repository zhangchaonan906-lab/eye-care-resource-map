\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_catalog, app_private, public, extensions;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eye_correction_submit') THEN
    CREATE ROLE eye_correction_submit NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

CREATE TABLE app_private.correction_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id uuid REFERENCES app_private.facilities(id) ON DELETE SET NULL,
  issue_type text NOT NULL CHECK (issue_type IN ('institution_info','moved','closed','ophthalmology_services','coordinates','source_issue')),
  description text NOT NULL CHECK (char_length(trim(description)) BETWEEN 10 AND 1000),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','reviewing','resolved','dismissed')),
  submitted_at timestamptz NOT NULL DEFAULT now(),
  reviewed_at timestamptz,
  reviewer_id uuid,
  review_note text CHECK (review_note IS NULL OR char_length(review_note) <= 500)
);
CREATE INDEX correction_reports_pending_idx ON app_private.correction_reports(submitted_at,id) WHERE status='pending';

CREATE FUNCTION app_private.submit_correction_report(p_facility_id uuid, p_issue_type text, p_description text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE report_id uuid;
BEGIN
  IF NOT pg_has_role(session_user,'eye_correction_submit','member') THEN
    RAISE EXCEPTION 'CORRECTION_SUBMIT_FORBIDDEN' USING ERRCODE='42501';
  END IF;
  IF p_issue_type IS NULL OR p_issue_type NOT IN ('institution_info','moved','closed','ophthalmology_services','coordinates','source_issue')
     OR p_description IS NULL OR char_length(trim(p_description)) NOT BETWEEN 10 AND 1000 THEN
    RAISE EXCEPTION 'CORRECTION_INPUT_INVALID' USING ERRCODE='22023';
  END IF;
  INSERT INTO app_private.correction_reports(facility_id,issue_type,description)
  VALUES(p_facility_id,p_issue_type,trim(p_description)) RETURNING id INTO report_id;
  RETURN report_id;
END;
$$;
REVOKE ALL ON app_private.correction_reports FROM PUBLIC;
REVOKE ALL ON FUNCTION app_private.submit_correction_report(uuid,text,text) FROM PUBLIC;
GRANT USAGE ON SCHEMA app_private TO eye_correction_submit;
GRANT EXECUTE ON FUNCTION app_private.submit_correction_report(uuid,text,text) TO eye_correction_submit;

CREATE VIEW app_private.admin_correction_review AS
SELECT r.id,r.facility_id,r.issue_type,r.description,r.status,r.submitted_at,r.reviewed_at,r.reviewer_id,r.review_note,
       f.name AS facility_name
FROM app_private.correction_reports r
LEFT JOIN app_private.facilities f ON f.id=r.facility_id;
GRANT SELECT ON app_private.admin_correction_review TO eye_admin_review;

CREATE FUNCTION app_private.admin_decide_correction_report(
  p_report_id uuid,p_actor_id uuid,p_request_id uuid,p_action text,p_note text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE report app_private.correction_reports%ROWTYPE; replay app_private.admin_idempotency%ROWTYPE;
        before_state jsonb; after_state jsonb; next_status text; result jsonb;
BEGIN
  IF NOT pg_has_role(session_user,'eye_admin_review','member') THEN
    RAISE EXCEPTION 'ADMIN_FORBIDDEN' USING ERRCODE='42501';
  END IF;
  IF p_action IS NULL OR p_action NOT IN ('START_REVIEW','RESOLVE','DISMISS') OR p_note IS NULL OR char_length(trim(p_note)) NOT BETWEEN 5 AND 500 THEN
    RAISE EXCEPTION 'CORRECTION_DECISION_INVALID' USING ERRCODE='22023';
  END IF;
  SELECT * INTO replay FROM app_private.admin_idempotency WHERE request_id=p_request_id FOR UPDATE;
  IF FOUND THEN
    IF replay.actor_id<>p_actor_id OR replay.entity<>'correction_report' OR replay.entity_id<>p_report_id OR replay.action<>p_action THEN
      RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT' USING ERRCODE='23505';
    END IF;
    RETURN replay.result;
  END IF;
  SELECT * INTO report FROM app_private.correction_reports WHERE id=p_report_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'CORRECTION_NOT_FOUND' USING ERRCODE='P0002'; END IF;
  next_status := CASE p_action
    WHEN 'START_REVIEW' THEN CASE WHEN report.status='pending' THEN 'reviewing' END
    WHEN 'RESOLVE' THEN CASE WHEN report.status='reviewing' THEN 'resolved' END
    WHEN 'DISMISS' THEN CASE WHEN report.status IN ('pending','reviewing') THEN 'dismissed' END
  END;
  IF next_status IS NULL THEN RAISE EXCEPTION 'CORRECTION_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
  before_state := to_jsonb(report);
  UPDATE app_private.correction_reports AS updated_report
  SET status=next_status,reviewed_at=now(),reviewer_id=p_actor_id,review_note=trim(p_note)
  WHERE id=p_report_id RETURNING to_jsonb(updated_report) INTO after_state;
  result := jsonb_build_object('reportId',p_report_id,'status',next_status);
  INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,before_value,after_value)
  VALUES(p_actor_id,'correction_report',p_report_id,p_action,trim(p_note),p_request_id,before_state,after_state);
  INSERT INTO app_private.admin_idempotency(request_id,actor_id,entity,entity_id,action,result)
  VALUES(p_request_id,p_actor_id,'correction_report',p_report_id,p_action,result);
  RETURN result;
END;
$$;
REVOKE ALL ON FUNCTION app_private.admin_decide_correction_report(uuid,uuid,uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_private.admin_decide_correction_report(uuid,uuid,uuid,text,text) TO eye_admin_review;
COMMIT;
