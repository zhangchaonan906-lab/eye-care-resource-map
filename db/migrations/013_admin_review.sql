\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_admin_review') THEN
    CREATE ROLE eye_admin_review NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

ALTER TABLE app_private.audit_events
  ADD COLUMN IF NOT EXISTS reason text,
  ADD COLUMN IF NOT EXISTS request_id uuid;
CREATE UNIQUE INDEX IF NOT EXISTS audit_events_request_id_uq
  ON app_private.audit_events(request_id) WHERE request_id IS NOT NULL;

-- Deferred integrity triggers can fire at transaction commit, after the
-- SECURITY DEFINER decision call has returned. Give these invariant checks a
-- fixed, privileged execution context instead of granting the admin role
-- direct read access to their backing tables.
CREATE OR REPLACE FUNCTION app_private.enforce_duplicate_case_min_members()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE target_case_id uuid;
BEGIN
  IF TG_TABLE_NAME='duplicate_cases' THEN
    target_case_id := CASE WHEN TG_OP='DELETE' THEN OLD.id ELSE NEW.id END;
  ELSE
    target_case_id := CASE WHEN TG_OP='DELETE' THEN OLD.duplicate_case_id ELSE NEW.duplicate_case_id END;
  END IF;
  IF EXISTS (SELECT 1 FROM app_private.duplicate_cases WHERE id=target_case_id)
     AND (SELECT count(*) FROM app_private.duplicate_case_candidates WHERE duplicate_case_id=target_case_id)<2 THEN
    RAISE EXCEPTION 'duplicate case % must have at least two candidates', target_case_id USING ERRCODE='23514';
  END IF;
  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION app_private.enforce_geocode_provider_policy()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp AS $$
DECLARE storage_allowed boolean;
BEGIN
  SELECT persistent_storage_allowed INTO storage_allowed FROM app_private.geocode_provider_policies
  WHERE provider=NEW.provider AND provider_version=NEW.provider_version;
  IF storage_allowed IS NULL THEN RAISE EXCEPTION 'geocode provider policy is missing' USING ERRCODE='23514'; END IF;
  IF NOT storage_allowed AND (NEW.provider_record_id IS NOT NULL OR NEW.returned_address IS NOT NULL
    OR NEW.returned_adcode IS NOT NULL OR NEW.longitude_wgs84 IS NOT NULL OR NEW.latitude_wgs84 IS NOT NULL
    OR NEW.accuracy_m IS NOT NULL OR NEW.source_metadata<>'{}'::jsonb) THEN
    RAISE EXCEPTION 'provider policy blocks persistence of provider response data' USING ERRCODE='23514';
  END IF;
  IF NOT storage_allowed AND (NEW.validation_status<>'needs_review' OR NEW.error_code IS DISTINCT FROM 'POLICY_BLOCKED') THEN
    RAISE EXCEPTION 'provider policy block must be recorded as needs_review' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS app_private.admin_idempotency (
  request_id uuid PRIMARY KEY,
  actor_id uuid NOT NULL,
  entity text NOT NULL,
  entity_id uuid NOT NULL,
  action text NOT NULL,
  result jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION app_private.reject_audit_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_events are immutable' USING ERRCODE = '55000';
END;
$$;
DROP TRIGGER IF EXISTS audit_events_immutable_trg ON app_private.audit_events;
CREATE TRIGGER audit_events_immutable_trg
BEFORE UPDATE OR DELETE ON app_private.audit_events
FOR EACH ROW EXECUTE FUNCTION app_private.reject_audit_mutation();

CREATE OR REPLACE VIEW app_private.admin_candidate_review AS
SELECT c.id, c.source_record_id, c.match_status, c.proposed_facility_id,
       c.parsed_fields ->> 'name' AS parsed_name,
       c.parsed_fields ->> 'address' AS parsed_address,
       c.normalized_name, c.normalized_address, c.administrative_code,
       c.registration_id, c.campus_name, c.processed_at,
       sr.source_url, sr.collected_at, sc.id AS source_id, sc.name AS source_name,
       sc.dataset_page AS source_page,
       COALESCE(jsonb_agg(DISTINCT jsonb_build_object(
         'fieldName', ce.field_name, 'evidenceText', ce.evidence_text,
         'evidenceType', ce.evidence_type, 'createdAt', ce.created_at
       )) FILTER (WHERE ce.id IS NOT NULL), '[]'::jsonb) AS ophthalmology_evidence
FROM app_private.candidate_records c
JOIN app_private.source_records sr ON sr.id = c.source_record_id
JOIN app_private.source_catalog sc ON sc.id = sr.source_id
LEFT JOIN app_private.candidate_evidence ce ON ce.candidate_record_id = c.id
GROUP BY c.id, sr.id, sc.id;

CREATE OR REPLACE VIEW app_private.admin_duplicate_review AS
SELECT dc.id, dc.reason, dc.score AS match_context_score, dc.resolution, dc.reviewer_id, dc.resolved_at,
       COALESCE(jsonb_agg(jsonb_build_object(
         'candidateId', c.id, 'name', c.parsed_fields ->> 'name',
         'address', c.parsed_fields ->> 'address', 'registrationId', c.registration_id,
         'region', c.administrative_code, 'sourceName', sc.name,
         'proposedFacilityId', c.proposed_facility_id, 'matchStatus', c.match_status
       ) ORDER BY c.id) FILTER (WHERE c.id IS NOT NULL), '[]'::jsonb) AS candidates
FROM app_private.duplicate_cases dc
LEFT JOIN app_private.duplicate_case_candidates members ON members.duplicate_case_id = dc.id
LEFT JOIN app_private.candidate_records c ON c.id = members.candidate_record_id
LEFT JOIN app_private.source_records sr ON sr.id = c.source_record_id
LEFT JOIN app_private.source_catalog sc ON sc.id = sr.source_id
GROUP BY dc.id;

CREATE OR REPLACE VIEW app_private.admin_location_review AS
SELECT cl.id, cl.candidate_record_id, cl.source_record_id, cl.provider, cl.provider_version,
       cl.query_address, cl.query_administrative_code, cl.returned_address, cl.returned_adcode,
       cl.longitude_wgs84, cl.latitude_wgs84, cl.accuracy_m, cl.precision_level,
       cl.validation_status, cl.validation_reason, cl.error_code, cl.verified_at,
       c.parsed_fields ->> 'name' AS candidate_name,
       c.parsed_fields ->> 'address' AS candidate_address,
       c.administrative_code AS candidate_administrative_code,
       gp.persistent_storage_allowed
FROM app_private.candidate_locations cl
JOIN app_private.candidate_records c ON c.id = cl.candidate_record_id
JOIN app_private.geocode_provider_policies gp
  ON gp.provider = cl.provider AND gp.provider_version = cl.provider_version;

CREATE OR REPLACE FUNCTION app_private.admin_publication_checklist(p_facility_id uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog, app_private, public, extensions, pg_temp AS $$
DECLARE f app_private.facilities%ROWTYPE; loc app_private.facility_locations%ROWTYPE;
        name_ok boolean; address_ok boolean; eye_ok boolean; coord_ok boolean;
        no_duplicate boolean; no_location_conflict boolean; rights_complete boolean;
        source_approved boolean; display_allowed boolean;
BEGIN
  SELECT * INTO f FROM app_private.facilities WHERE id = p_facility_id;
  IF NOT FOUND THEN RETURN jsonb_build_object('exists', false); END IF;
  SELECT * INTO loc FROM app_private.facility_locations WHERE facility_id = p_facility_id;
  SELECT EXISTS (
    SELECT 1 FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id=e.source_record_id
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name='name' AND e.field_value=to_jsonb(f.name)
      AND s.status='approved' AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE
      AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown'
      AND 'name'=ANY(s.permitted_fields)
  ) INTO name_ok;
  SELECT EXISTS (
    SELECT 1 FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id=e.source_record_id
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name='address' AND e.field_value=to_jsonb(f.address)
      AND s.status='approved' AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE
      AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown'
      AND 'address'=ANY(s.permitted_fields)
  ) INTO address_ok;
  SELECT EXISTS (
    SELECT 1 FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id=e.source_record_id
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description')
      AND s.status='approved' AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE
      AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown'
      AND e.field_name=ANY(s.permitted_fields)
  ) INTO eye_ok;
  SELECT EXISTS (
    SELECT 1 FROM app_private.source_records sr
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE sr.id=loc.coordinate_source_record_id AND s.status='approved'
      AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE
      AND s.retention_restrictions <> 'unknown' AND 'coordinates'=ANY(s.permitted_fields)
  ) INTO coord_ok;
  SELECT EXISTS (SELECT 1 FROM app_private.source_records sr
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE sr.id=loc.coordinate_source_record_id AND s.status='approved')
    INTO source_approved;
  SELECT NOT EXISTS (
    SELECT 1 FROM app_private.duplicate_case_candidates m
    JOIN app_private.candidate_records c ON c.id=m.candidate_record_id
    JOIN app_private.duplicate_cases d ON d.id=m.duplicate_case_id
    WHERE c.proposed_facility_id=f.id AND d.resolution='pending'
  ) INTO no_duplicate;
  SELECT NOT EXISTS (
    SELECT 1 FROM app_private.candidate_records c
    JOIN app_private.candidate_locations cl ON cl.candidate_record_id=c.id
    WHERE c.proposed_facility_id=f.id AND cl.validation_status='needs_review'
      AND (cl.longitude_wgs84 IS NULL OR cl.returned_adcode IS DISTINCT FROM
           (SELECT adcode FROM app_private.regions WHERE id=f.region_id)
        OR loc.geog_wgs84 IS NULL OR ST_Distance(
           ST_SetSRID(ST_MakePoint(cl.longitude_wgs84,cl.latitude_wgs84),4326)::geography,
           loc.geog_wgs84) > 100)
  ) INTO no_location_conflict;
  rights_complete := name_ok AND address_ok AND eye_ok AND coord_ok;
  display_allowed := name_ok AND address_ok AND eye_ok AND coord_ok;
  RETURN jsonb_build_object(
    'exists', true, 'nameEvidence', COALESCE(name_ok,false),
    'addressEvidence', COALESCE(address_ok,false), 'ophthalmologyEvidence', COALESCE(eye_ok,false),
    'locationVerified', COALESCE(loc.location_status='verified' AND loc.verified_at IS NOT NULL,false),
    'coordinateSourceApproved', COALESCE(source_approved,false),
    'sourceAppDisplayAllowed', COALESCE(display_allowed,false),
    'pendingDuplicateClear', COALESCE(no_duplicate,false),
    'locationConflictClear', COALESCE(no_location_conflict,false),
    'rightsMetadataComplete', COALESCE(rights_complete,false),
    'blockers', to_jsonb(ARRAY_REMOVE(ARRAY[
      CASE WHEN f.verification_status <> 'verified' THEN 'FACILITY_NOT_VERIFIED' END,
      CASE WHEN f.ophthalmology_status <> 'verified' THEN 'OPHTHALMOLOGY_NOT_VERIFIED' END,
      CASE WHEN f.last_verified_at IS NULL THEN 'FACILITY_NOT_VERIFIED' END,
      CASE WHEN NOT COALESCE(loc.location_status='verified' AND loc.verified_at IS NOT NULL,false) THEN 'LOCATION_NOT_VERIFIED' END,
      CASE WHEN NOT COALESCE(name_ok,false) THEN 'NAME_EVIDENCE_OR_RIGHTS_INVALID' END,
      CASE WHEN NOT COALESCE(address_ok,false) THEN 'ADDRESS_EVIDENCE_OR_RIGHTS_INVALID' END,
      CASE WHEN NOT COALESCE(eye_ok,false) THEN 'OPHTHALMOLOGY_EVIDENCE_OR_RIGHTS_INVALID' END,
      CASE WHEN NOT COALESCE(coord_ok,false) THEN 'RIGHTS_METADATA_INCOMPLETE' END,
      CASE WHEN NOT COALESCE(no_duplicate,false) THEN 'PENDING_DUPLICATE_REVIEW' END,
      CASE WHEN NOT COALESCE(no_location_conflict,false) THEN 'LOCATION_AMBIGUITY' END
    ], NULL))
  );
END;
$$;

CREATE OR REPLACE VIEW app_private.admin_facility_review AS
SELECT f.id, f.name, f.address, f.category, f.campus_name, f.hospital_level,
       f.hospital_grade, f.verification_status, f.ophthalmology_status,
       f.last_verified_at, f.published_at, r.adcode AS region_adcode, r.name AS region_name,
       app_private.admin_publication_checklist(f.id) AS publication_checklist
FROM app_private.facilities f JOIN app_private.regions r ON r.id=f.region_id;

CREATE OR REPLACE VIEW app_private.admin_import_runs AS
SELECT ir.id, sc.name AS source_name, ir.region_code, ir.status, ir.started_at,
       ir.ended_at, ir.counts, ir.error_summary
FROM app_private.import_runs ir JOIN app_private.source_catalog sc ON sc.id=ir.source_id;

CREATE OR REPLACE VIEW app_private.admin_audit_feed AS
SELECT id, actor_id, entity, entity_id, action, reason, request_id,
       before_value, after_value, created_at
FROM app_private.audit_events;

CREATE OR REPLACE FUNCTION app_private.admin_decide(
  p_request_id uuid, p_actor_id uuid, p_entity text, p_entity_id uuid,
  p_action text, p_payload jsonb, p_reason text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, app_private, public, extensions, pg_temp AS $$
DECLARE replay app_private.admin_idempotency%ROWTYPE; before_state jsonb; after_state jsonb;
        result jsonb; candidate_id uuid; facility_id uuid; source_id uuid; region_uuid uuid;
        current_status text; member_ids uuid[]; location_row app_private.candidate_locations%ROWTYPE;
        target_facility_id uuid; new_facility_id uuid; checklist jsonb; audit_action text;
        last_merge jsonb; member_state record;
BEGIN
  IF NOT pg_has_role(session_user, 'eye_admin_review', 'member') THEN
    RAISE EXCEPTION 'ADMIN_FORBIDDEN' USING ERRCODE='42501';
  END IF;
  IF p_request_id IS NULL OR p_actor_id IS NULL OR p_payload IS NULL THEN
    RAISE EXCEPTION 'INVALID_ARGUMENT' USING ERRCODE='22023';
  END IF;
  IF length(trim(COALESCE(p_reason,''))) < 5 OR length(trim(p_reason)) > 500 THEN
    RAISE EXCEPTION 'REASON_REQUIRED' USING ERRCODE='22023';
  END IF;
  SELECT * INTO replay FROM app_private.admin_idempotency WHERE request_id=p_request_id FOR UPDATE;
  IF FOUND THEN
    IF replay.actor_id<>p_actor_id OR replay.entity<>p_entity OR replay.entity_id<>p_entity_id OR replay.action<>p_action THEN
      RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED' USING ERRCODE='22023';
    END IF;
    RETURN replay.result;
  END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended(p_request_id::text, 1));
  SELECT * INTO replay FROM app_private.admin_idempotency WHERE request_id=p_request_id;
  IF FOUND THEN RETURN replay.result; END IF;

  IF p_entity='candidate' THEN
    SELECT to_jsonb(c) INTO STRICT before_state FROM app_private.candidate_records c WHERE id=p_entity_id FOR UPDATE;
    candidate_id := p_entity_id;
    IF p_action='CREATE_FACILITY' THEN
      IF before_state->>'match_status' NOT IN ('unmatched','needs_review') THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      IF COALESCE(p_payload->>'name','')='' OR COALESCE(p_payload->>'address','')=''
        OR (COALESCE(p_payload->>'regionId','')='' AND COALESCE(p_payload->>'regionCode','')='')
        OR COALESCE(p_payload->>'category','') NOT IN ('eye_specialty_hospital','general_hospital_ophthalmology','ophthalmology_center','eye_clinic','unknown') THEN RAISE EXCEPTION 'INVALID_ARGUMENT' USING ERRCODE='22023'; END IF;
      IF COALESCE(p_payload->>'regionCode','')<>'' THEN
        SELECT id INTO region_uuid FROM app_private.regions WHERE adcode=p_payload->>'regionCode' ORDER BY valid_from DESC NULLS LAST,version DESC LIMIT 1;
      ELSE
        region_uuid := (p_payload->>'regionId')::uuid;
      END IF;
      IF NOT EXISTS (SELECT 1 FROM app_private.regions WHERE id=region_uuid) THEN RAISE EXCEPTION 'INVALID_REGION' USING ERRCODE='22023'; END IF;
      SELECT source_record_id INTO source_id FROM app_private.candidate_records WHERE id=candidate_id;
      INSERT INTO app_private.facilities(name,normalized_name,campus_name,category,region_id,address,hospital_level,hospital_grade,verification_status)
      VALUES (trim(p_payload->>'name'), trim(p_payload->>'name'), NULLIF(trim(p_payload->>'campusName'),''), p_payload->>'category', region_uuid,
              trim(p_payload->>'address'), NULLIF(trim(p_payload->>'hospitalLevel'),''), NULLIF(trim(p_payload->>'hospitalGrade'),''), 'in_review')
      RETURNING id INTO facility_id;
      IF p_payload->>'name' = (SELECT parsed_fields->>'name' FROM app_private.candidate_records WHERE id=candidate_id) THEN
        INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value)
        VALUES(facility_id,source_id,'name',to_jsonb(p_payload->>'name')) ON CONFLICT DO NOTHING;
      END IF;
      IF p_payload->>'address' = (SELECT parsed_fields->>'address' FROM app_private.candidate_records WHERE id=candidate_id) THEN
        INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value)
        VALUES(facility_id,source_id,'address',to_jsonb(p_payload->>'address')) ON CONFLICT DO NOTHING;
      END IF;
      INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
      SELECT facility_id,ce.source_record_id,ce.field_name,ce.evidence_value,1,now()
      FROM app_private.candidate_evidence ce WHERE ce.candidate_record_id=candidate_id ON CONFLICT DO NOTHING;
      UPDATE app_private.candidate_records SET match_status='matched',proposed_facility_id=facility_id WHERE id=candidate_id;
      audit_action := p_action;
    ELSIF p_action='MATCH_EXISTING_FACILITY' THEN
      IF before_state->>'match_status' NOT IN ('unmatched','needs_review') THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      target_facility_id := (p_payload->>'targetFacilityId')::uuid;
      PERFORM 1 FROM app_private.facilities WHERE id=target_facility_id AND verification_status<>'withdrawn' FOR UPDATE;
      IF NOT FOUND THEN RAISE EXCEPTION 'FACILITY_NOT_FOUND' USING ERRCODE='P0002'; END IF;
      SELECT source_record_id INTO source_id FROM app_private.candidate_records WHERE id=candidate_id;
      INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value)
      SELECT target_facility_id,source_id,key,to_jsonb(value)
      FROM app_private.candidate_records c CROSS JOIN LATERAL jsonb_each_text(c.parsed_fields) fields(key,value)
      WHERE c.id=candidate_id AND key IN ('name','address')
        AND value=CASE key WHEN 'name' THEN (SELECT name FROM app_private.facilities WHERE id=target_facility_id) ELSE (SELECT address FROM app_private.facilities WHERE id=target_facility_id) END
      ON CONFLICT DO NOTHING;
      INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
      SELECT target_facility_id,ce.source_record_id,ce.field_name,ce.evidence_value,1,now()
      FROM app_private.candidate_evidence ce WHERE ce.candidate_record_id=candidate_id ON CONFLICT DO NOTHING;
      UPDATE app_private.candidate_records SET match_status='matched',proposed_facility_id=target_facility_id WHERE id=candidate_id;
      facility_id := target_facility_id; audit_action := p_action;
    ELSIF p_action='REJECT_CANDIDATE' THEN
      IF before_state->>'match_status'='rejected' THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      UPDATE app_private.candidate_records SET match_status='rejected',proposed_facility_id=NULL WHERE id=candidate_id;
      audit_action := p_action;
    ELSE RAISE EXCEPTION 'INVALID_ACTION' USING ERRCODE='22023'; END IF;
    SELECT to_jsonb(c) INTO after_state FROM app_private.candidate_records c WHERE c.id=candidate_id;
    result := jsonb_build_object('entityId',candidate_id,'facilityId',facility_id,'action',p_action);
    INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,before_value,after_value)
    VALUES(p_actor_id,'candidate',candidate_id,audit_action,trim(p_reason),p_request_id,before_state,after_state || jsonb_build_object('facility_id',facility_id));

  ELSIF p_entity='duplicate' THEN
    SELECT to_jsonb(d) INTO STRICT before_state FROM app_private.duplicate_cases d WHERE id=p_entity_id FOR UPDATE;
    SELECT array_agg(candidate_record_id ORDER BY candidate_record_id) INTO member_ids FROM app_private.duplicate_case_candidates WHERE duplicate_case_id=p_entity_id;
    IF COALESCE(array_length(member_ids,1),0)<2 THEN RAISE EXCEPTION 'DUPLICATE_CASE_REQUIRES_TWO_MEMBERS' USING ERRCODE='23514'; END IF;
    IF p_action IN ('MERGE','SEPARATE','REJECT_DUPLICATE') THEN
      IF (before_state->>'resolution')<>'pending' THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      SELECT COALESCE(jsonb_agg(jsonb_build_object('id',id,'match_status',match_status,'proposed_facility_id',proposed_facility_id)), '[]'::jsonb)
      INTO after_state FROM app_private.candidate_records WHERE id=ANY(member_ids);
      IF p_action='MERGE' THEN
        target_facility_id := NULLIF(p_payload->>'targetFacilityId','')::uuid;
        IF target_facility_id IS NULL THEN
          candidate_id := (p_payload->>'primaryCandidateId')::uuid;
          IF NOT candidate_id=ANY(member_ids) THEN RAISE EXCEPTION 'INVALID_PRIMARY_CANDIDATE' USING ERRCODE='22023'; END IF;
          SELECT source_record_id INTO source_id FROM app_private.candidate_records WHERE id=candidate_id;
          IF COALESCE(p_payload->>'regionCode','')<>'' THEN
            SELECT id INTO region_uuid FROM app_private.regions WHERE adcode=p_payload->>'regionCode' ORDER BY valid_from DESC NULLS LAST,version DESC LIMIT 1;
          ELSE
            region_uuid := (p_payload->>'regionId')::uuid;
          END IF;
          INSERT INTO app_private.facilities(name,normalized_name,category,region_id,address,verification_status)
          VALUES(trim(p_payload->>'name'),trim(p_payload->>'name'),p_payload->>'category',region_uuid,trim(p_payload->>'address'),'in_review')
          RETURNING id INTO target_facility_id;
          new_facility_id := target_facility_id;
          INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value)
          SELECT target_facility_id,source_id,key,to_jsonb(value)
          FROM app_private.candidate_records c CROSS JOIN LATERAL jsonb_each_text(c.parsed_fields) fields(key,value)
          WHERE c.id=candidate_id AND key IN ('name','address') AND value=CASE key WHEN 'name' THEN p_payload->>'name' ELSE p_payload->>'address' END
          ON CONFLICT DO NOTHING;
          INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
          SELECT target_facility_id,ce.source_record_id,ce.field_name,ce.evidence_value,1,now()
          FROM app_private.candidate_evidence ce WHERE ce.candidate_record_id=candidate_id ON CONFLICT DO NOTHING;
        ELSE
          PERFORM 1 FROM app_private.facilities WHERE id=target_facility_id AND verification_status<>'withdrawn' FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'FACILITY_NOT_FOUND' USING ERRCODE='P0002'; END IF;
        END IF;
        INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value)
        SELECT target_facility_id,c.source_record_id,'name',to_jsonb(c.parsed_fields->>'name')
        FROM app_private.candidate_records c JOIN app_private.facilities f ON f.id=target_facility_id
        WHERE c.id=ANY(member_ids) AND c.parsed_fields->>'name'=f.name
        ON CONFLICT DO NOTHING;
        INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value)
        SELECT target_facility_id,c.source_record_id,'address',to_jsonb(c.parsed_fields->>'address')
        FROM app_private.candidate_records c JOIN app_private.facilities f ON f.id=target_facility_id
        WHERE c.id=ANY(member_ids) AND c.parsed_fields->>'address'=f.address
        ON CONFLICT DO NOTHING;
        INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
        SELECT target_facility_id,ce.source_record_id,ce.field_name,ce.evidence_value,1,now()
        FROM app_private.candidate_evidence ce WHERE ce.candidate_record_id=ANY(member_ids)
        ON CONFLICT DO NOTHING;
        UPDATE app_private.candidate_records SET match_status='matched',proposed_facility_id=target_facility_id WHERE id=ANY(member_ids);
        UPDATE app_private.duplicate_cases SET resolution='merge',reviewer_id=p_actor_id,resolved_at=now() WHERE id=p_entity_id;
      ELSE
        UPDATE app_private.duplicate_cases SET resolution=CASE WHEN p_action='SEPARATE' THEN 'separate' ELSE 'reject' END,reviewer_id=p_actor_id,resolved_at=now() WHERE id=p_entity_id;
      END IF;
      audit_action := p_action;
      after_state := jsonb_build_object('resolution',CASE WHEN p_action='MERGE' THEN 'merge' WHEN p_action='SEPARATE' THEN 'separate' ELSE 'reject' END,
        'reviewer_id',p_actor_id,'resolved_at',now(),'members',after_state,'created_facility_id',new_facility_id);
    ELSIF p_action='REOPEN_DUPLICATE_CASE' THEN
      IF (before_state->>'resolution')='pending' THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      SELECT after_value INTO last_merge FROM app_private.audit_events
       WHERE entity='duplicate' AND entity_id=p_entity_id AND action IN ('MERGE','SEPARATE','REJECT_DUPLICATE') ORDER BY created_at DESC LIMIT 1;
      IF last_merge IS NULL OR last_merge->'members' IS NULL THEN RAISE EXCEPTION 'REOPEN_STATE_UNAVAILABLE' USING ERRCODE='55000'; END IF;
      FOR member_state IN SELECT * FROM jsonb_to_recordset(last_merge->'members') AS x(id uuid,match_status text,proposed_facility_id uuid) LOOP
        UPDATE app_private.candidate_records SET match_status=member_state.match_status, proposed_facility_id=member_state.proposed_facility_id WHERE id=member_state.id;
      END LOOP;
      UPDATE app_private.duplicate_cases SET resolution='pending',reviewer_id=NULL,resolved_at=NULL WHERE id=p_entity_id;
      new_facility_id := NULLIF(last_merge->>'created_facility_id','')::uuid;
      IF new_facility_id IS NOT NULL THEN UPDATE app_private.facilities SET verification_status='in_review' WHERE id=new_facility_id AND verification_status IN ('in_review','verified'); END IF;
      audit_action := p_action; after_state := jsonb_build_object('resolution','pending','restoredFrom',last_merge);
    ELSE RAISE EXCEPTION 'INVALID_ACTION' USING ERRCODE='22023'; END IF;
    result := jsonb_build_object('entityId',p_entity_id,'action',p_action,'facilityId',target_facility_id);
    INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,before_value,after_value)
    VALUES(p_actor_id,'duplicate',p_entity_id,audit_action,trim(p_reason),p_request_id,before_state,after_state);

  ELSIF p_entity='location' THEN
    SELECT * INTO STRICT location_row FROM app_private.candidate_locations WHERE id=p_entity_id FOR UPDATE;
    before_state := to_jsonb(location_row);
    IF p_action='VERIFY_LOCATION' THEN
      IF location_row.validation_status<>'needs_review' OR NOT EXISTS (
        SELECT 1 FROM app_private.geocode_provider_policies gp WHERE gp.provider=location_row.provider AND gp.provider_version=location_row.provider_version AND gp.persistent_storage_allowed
      ) THEN RAISE EXCEPTION 'LOCATION_NOT_ELIGIBLE' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS (SELECT 1 FROM app_private.candidate_records c WHERE c.id=location_row.candidate_record_id
        AND c.administrative_code IS NOT NULL AND c.administrative_code=location_row.returned_adcode) THEN
        RAISE EXCEPTION 'LOCATION_REGION_MISMATCH' USING ERRCODE='23514';
      END IF;
      UPDATE app_private.candidate_locations SET validation_status='verified',error_code=NULL,validation_reason=NULL,verified_at=now() WHERE id=p_entity_id;
    ELSIF p_action='REJECT_LOCATION' THEN
      IF location_row.validation_status='rejected' THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      UPDATE app_private.candidate_locations SET validation_status='rejected',error_code='AMBIGUOUS_RESULT',validation_reason=trim(p_reason),verified_at=NULL WHERE id=p_entity_id;
    ELSIF p_action='PROMOTE_LOCATION' THEN
      IF location_row.validation_status<>'verified' OR location_row.verified_at IS NULL THEN RAISE EXCEPTION 'LOCATION_NOT_VERIFIED' USING ERRCODE='23514'; END IF;
      SELECT proposed_facility_id INTO target_facility_id FROM app_private.candidate_records WHERE id=location_row.candidate_record_id AND match_status='matched' FOR UPDATE;
      IF target_facility_id IS NULL THEN RAISE EXCEPTION 'CANDIDATE_NOT_MATCHED' USING ERRCODE='23514'; END IF;
      IF EXISTS (SELECT 1 FROM app_private.facility_locations fl WHERE fl.facility_id=target_facility_id AND fl.location_status='verified') AND COALESCE((p_payload->>'replaceVerified')::boolean,false) IS NOT TRUE THEN
        RAISE EXCEPTION 'VERIFIED_LOCATION_REPLACEMENT_CONFIRMATION_REQUIRED' USING ERRCODE='23514';
      END IF;
      SELECT to_jsonb(fl) INTO before_state FROM app_private.facility_locations fl WHERE fl.facility_id=target_facility_id FOR UPDATE;
      INSERT INTO app_private.facility_locations(facility_id,geog_wgs84,coordinate_source_record_id,accuracy_m,location_status,verified_at)
      VALUES(target_facility_id,ST_SetSRID(ST_MakePoint(location_row.longitude_wgs84,location_row.latitude_wgs84),4326)::geography,
             location_row.source_record_id,location_row.accuracy_m,'verified',location_row.verified_at)
      ON CONFLICT ON CONSTRAINT facility_locations_pkey DO UPDATE SET geog_wgs84=EXCLUDED.geog_wgs84,coordinate_source_record_id=EXCLUDED.coordinate_source_record_id,
        accuracy_m=EXCLUDED.accuracy_m,location_status='verified',verified_at=EXCLUDED.verified_at;
    ELSE RAISE EXCEPTION 'INVALID_ACTION' USING ERRCODE='22023'; END IF;
    SELECT to_jsonb(cl) INTO after_state FROM app_private.candidate_locations cl WHERE id=p_entity_id;
    result := jsonb_build_object('entityId',p_entity_id,'action',p_action,'facilityId',target_facility_id);
    INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,before_value,after_value)
    VALUES(p_actor_id,'location',p_entity_id,p_action,trim(p_reason),p_request_id,before_state,after_state);

  ELSIF p_entity='facility' THEN
    SELECT to_jsonb(f) INTO STRICT before_state FROM app_private.facilities f WHERE id=p_entity_id FOR UPDATE;
    current_status := before_state->>'verification_status';
    IF p_action='VERIFY_FACILITY' THEN
      IF current_status<>'in_review' OR btrim(COALESCE(before_state->>'name',''))='' OR btrim(COALESCE(before_state->>'address',''))=''
        OR before_state->>'region_id' IS NULL
        OR NOT EXISTS(SELECT 1 FROM app_private.facility_locations l WHERE l.facility_id=p_entity_id AND l.location_status='verified' AND l.verified_at IS NOT NULL)
        OR NOT EXISTS(SELECT 1 FROM app_private.facility_evidence e WHERE e.facility_id=p_entity_id AND e.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description')) THEN
        RAISE EXCEPTION 'FACILITY_VERIFICATION_BLOCKED' USING ERRCODE='23514';
      END IF;
      UPDATE app_private.facilities SET verification_status='verified',ophthalmology_status='verified',last_verified_at=now(),updated_at=now() WHERE id=p_entity_id;
      INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
      SELECT p_entity_id,e.source_record_id,'ophthalmology_status','"verified"'::jsonb,1,now()
      FROM app_private.facility_evidence e WHERE e.facility_id=p_entity_id AND e.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description')
      ORDER BY e.id LIMIT 1 ON CONFLICT DO NOTHING;
    ELSIF p_action='PUBLISH' THEN
      IF current_status<>'verified' THEN RAISE EXCEPTION 'FACILITY_NOT_VERIFIED' USING ERRCODE='23514'; END IF;
      checklist := app_private.admin_publication_checklist(p_entity_id);
      IF checklist->'blockers' <> '[]'::jsonb THEN RAISE EXCEPTION 'PUBLISH_BLOCKED:%', checklist->'blockers' USING ERRCODE='23514'; END IF;
      UPDATE app_private.facilities SET verification_status='published',published_at=now(),updated_at=now() WHERE id=p_entity_id;
    ELSIF p_action='RETURN_TO_REVIEW' THEN
      IF current_status NOT IN ('verified','published') THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      UPDATE app_private.facilities SET verification_status='in_review',ophthalmology_status=CASE WHEN EXISTS(SELECT 1 FROM app_private.facility_evidence fe WHERE fe.facility_id=p_entity_id AND fe.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description')) THEN 'verified' ELSE 'unknown' END,updated_at=now() WHERE id=p_entity_id;
    ELSIF p_action='WITHDRAW' THEN
      IF current_status<>'published' THEN RAISE EXCEPTION 'REVIEW_STATE_CONFLICT' USING ERRCODE='40001'; END IF;
      UPDATE app_private.facilities SET verification_status='withdrawn',updated_at=now() WHERE id=p_entity_id;
    ELSE RAISE EXCEPTION 'INVALID_ACTION' USING ERRCODE='22023'; END IF;
    SELECT to_jsonb(f) INTO after_state FROM app_private.facilities f WHERE id=p_entity_id;
    result := jsonb_build_object('entityId',p_entity_id,'action',p_action,'checklist',CASE WHEN p_action='PUBLISH' THEN checklist ELSE NULL END);
    INSERT INTO app_private.audit_events(actor_id,entity,entity_id,action,reason,request_id,before_value,after_value)
    VALUES(p_actor_id,'facility',p_entity_id,p_action,trim(p_reason),p_request_id,before_state,after_state);
  ELSE RAISE EXCEPTION 'INVALID_ENTITY' USING ERRCODE='22023'; END IF;

  INSERT INTO app_private.admin_idempotency(request_id,actor_id,entity,entity_id,action,result)
  VALUES(p_request_id,p_actor_id,p_entity,p_entity_id,p_action,result);
  RETURN result;
END;
$$;

REVOKE ALL ON FUNCTION app_private.admin_decide(uuid,uuid,text,uuid,text,jsonb,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION app_private.admin_publication_checklist(uuid) FROM PUBLIC;
GRANT USAGE ON SCHEMA app_private TO eye_admin_review;
GRANT SELECT ON app_private.admin_candidate_review, app_private.admin_duplicate_review,
  app_private.admin_location_review, app_private.admin_facility_review,
  app_private.admin_import_runs, app_private.admin_audit_feed TO eye_admin_review;
GRANT EXECUTE ON FUNCTION app_private.admin_decide(uuid,uuid,text,uuid,text,jsonb,text),
  app_private.admin_publication_checklist(uuid) TO eye_admin_review;

CREATE OR REPLACE VIEW public.published_facilities WITH (security_barrier = true) AS
SELECT f.id, f.name, f.campus_name, f.category, f.address, f.phone, f.website,
       f.hospital_level, f.hospital_grade, r.adcode AS region_adcode, r.name AS region_name,
       f.last_verified_at, l.geog_wgs84,
       ST_X(l.geog_wgs84::geometry) AS longitude_wgs84,
       ST_Y(l.geog_wgs84::geometry) AS latitude_wgs84
FROM app_private.facilities f
JOIN app_private.regions r ON r.id=f.region_id
JOIN app_private.facility_locations l ON l.facility_id=f.id
JOIN app_private.source_records cr ON cr.id=l.coordinate_source_record_id
JOIN app_private.source_catalog cs ON cs.id=cr.source_id
WHERE f.verification_status='published' AND f.published_at IS NOT NULL
  AND f.last_verified_at IS NOT NULL AND f.ophthalmology_status='verified'
  AND l.location_status='verified' AND l.verified_at IS NOT NULL
  AND cs.status='approved' AND cs.data_use_allowed IS TRUE AND cs.reuse_allowed IS TRUE
  AND cs.app_display_allowed IS TRUE AND cs.retention_restrictions <> 'unknown'
  AND 'coordinates'=ANY(cs.permitted_fields)
  AND EXISTS (SELECT 1 FROM app_private.facility_evidence e JOIN app_private.source_records sr ON sr.id=e.source_record_id JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name='ophthalmology_status' AND e.field_value='"verified"'::jsonb AND s.status='approved'
      AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown')
  AND EXISTS (SELECT 1 FROM app_private.facility_evidence e JOIN app_private.source_records sr ON sr.id=e.source_record_id JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name='name' AND e.field_value=to_jsonb(f.name) AND s.status='approved'
      AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown' AND 'name'=ANY(s.permitted_fields))
  AND EXISTS (SELECT 1 FROM app_private.facility_evidence e JOIN app_private.source_records sr ON sr.id=e.source_record_id JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name='address' AND e.field_value=to_jsonb(f.address) AND s.status='approved'
      AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown' AND 'address'=ANY(s.permitted_fields))
  AND EXISTS (SELECT 1 FROM app_private.facility_evidence e JOIN app_private.source_records sr ON sr.id=e.source_record_id JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND e.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description') AND s.status='approved'
      AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown' AND e.field_name=ANY(s.permitted_fields));
REVOKE ALL ON public.published_facilities FROM PUBLIC;

CREATE OR REPLACE VIEW public.published_facility_api WITH (security_barrier = true) AS
SELECT p.id, p.name, f.normalized_name, p.category, p.address, p.region_adcode, p.region_name,
       p.hospital_level, p.hospital_grade, p.geog_wgs84, p.longitude_wgs84, p.latitude_wgs84,
       p.last_verified_at, COALESCE(evidence.ophthalmology_evidence_count,0)::integer AS ophthalmology_evidence_count,
       COALESCE(attribution.items,'[]'::jsonb) AS attribution
FROM public.published_facilities p
JOIN app_private.facilities f ON f.id=p.id
LEFT JOIN LATERAL (
  SELECT count(*)::integer AS ophthalmology_evidence_count
  FROM app_private.facility_evidence e
  JOIN app_private.source_records sr ON sr.id=e.source_record_id
  JOIN app_private.source_catalog s ON s.id=sr.source_id
  WHERE e.facility_id=f.id AND e.field_name='ophthalmology_status' AND e.field_value='"verified"'::jsonb
    AND s.status='approved' AND s.data_use_allowed IS TRUE AND s.reuse_allowed IS TRUE
    AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown'
    AND EXISTS (SELECT 1 FROM app_private.facility_evidence actual
      WHERE actual.facility_id=f.id AND actual.source_record_id=sr.id
        AND actual.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description')
        AND actual.field_name=ANY(s.permitted_fields))
) evidence ON true
LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object('name',sources.name,'url',sources.url,'updatedAt',sources.updated_at)
    ORDER BY sources.name,sources.url,sources.updated_at) AS items
  FROM (
    SELECT DISTINCT s.name,COALESCE(s.dataset_page,s.url) AS url,s.source_updated_at AS updated_at
    FROM app_private.facility_evidence e
    JOIN app_private.source_records sr ON sr.id=e.source_record_id
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE e.facility_id=f.id AND s.status='approved' AND s.data_use_allowed IS TRUE
      AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown'
      AND ((e.field_name='name' AND 'name'=ANY(s.permitted_fields))
        OR (e.field_name='address' AND 'address'=ANY(s.permitted_fields))
        OR (e.field_name IN ('ophthalmology_services','departments','department_text','specialties','hospital_description')
          AND e.field_name=ANY(s.permitted_fields)))
    UNION
    SELECT DISTINCT s.name,COALESCE(s.dataset_page,s.url),s.source_updated_at
    FROM app_private.facility_locations l
    JOIN app_private.source_records sr ON sr.id=l.coordinate_source_record_id
    JOIN app_private.source_catalog s ON s.id=sr.source_id
    WHERE l.facility_id=f.id AND s.status='approved' AND s.data_use_allowed IS TRUE
      AND s.reuse_allowed IS TRUE AND s.app_display_allowed IS TRUE AND s.retention_restrictions <> 'unknown'
      AND 'coordinates'=ANY(s.permitted_fields)
  ) sources
) attribution ON true;

COMMIT;
