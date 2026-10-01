\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

ALTER TABLE app_private.source_catalog
  ADD COLUMN platform text,
  ADD COLUMN dataset_page text CHECK (dataset_page IS NULL OR dataset_page ~ '^https://'),
  ADD COLUMN data_provider text,
  ADD COLUMN open_condition text,
  ADD COLUMN license_url text CHECK (license_url IS NULL OR license_url ~ '^https://'),
  ADD COLUMN source_updated_at date,
  ADD COLUMN data_use_allowed boolean,
  ADD COLUMN reuse_allowed boolean,
  ADD COLUMN app_display_allowed boolean,
  ADD COLUMN raw_data_transfer_allowed boolean,
  ADD COLUMN raw_data_redistribution_allowed boolean,
  ADD COLUMN attribution_required boolean,
  ADD COLUMN attribution_text text,
  ADD COLUMN retention_restrictions text NOT NULL DEFAULT 'unknown'
    CHECK (retention_restrictions IN ('unrestricted', 'delete_on_withdrawal', 'unknown')),
  ADD COLUMN pilot_group text,
  ADD COLUMN pilot_group_record_limit integer
    CHECK (pilot_group_record_limit IS NULL OR pilot_group_record_limit > 0),
  ADD CONSTRAINT source_catalog_shenzhen_transfer_guard CHECK (
    platform IS DISTINCT FROM '深圳市政府数据开放平台'
    OR (raw_data_transfer_allowed IS NOT TRUE AND raw_data_redistribution_allowed IS NOT TRUE)
  );

CREATE FUNCTION app_private.enforce_pilot_source_record_limit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  group_key text;
  group_limit integer;
  current_count bigint;
BEGIN
  SELECT pilot_group, pilot_group_record_limit
  INTO group_key, group_limit
  FROM app_private.source_catalog
  WHERE id = NEW.source_id;

  IF group_key IS NULL OR group_limit IS NULL THEN
    RETURN NEW;
  END IF;

  PERFORM pg_advisory_xact_lock(hashtextextended(group_key, 0));
  IF EXISTS (
    SELECT 1
    FROM app_private.source_records AS records
    WHERE records.source_id = NEW.source_id
      AND records.source_key = NEW.source_key
      AND records.content_hash = NEW.content_hash
  ) THEN
    RETURN NEW;
  END IF;

  SELECT count(*) INTO current_count
  FROM app_private.source_records AS records
  JOIN app_private.source_catalog AS sources ON sources.id = records.source_id
  WHERE sources.pilot_group = group_key;

  IF current_count >= group_limit THEN
    RAISE EXCEPTION 'pilot source record limit reached for group %', group_key
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER source_records_pilot_limit_trg
BEFORE INSERT ON app_private.source_records
FOR EACH ROW EXECUTE FUNCTION app_private.enforce_pilot_source_record_limit();

CREATE OR REPLACE FUNCTION app_private.reject_source_record_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF current_setting('app.allow_source_erasure', true) = 'true' THEN
    IF TG_OP = 'DELETE' THEN
      RETURN OLD;
    END IF;
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'source_records are immutable; insert a new snapshot instead'
    USING ERRCODE = '55000';
END;
$$;

CREATE OR REPLACE FUNCTION app_private.erase_withdrawn_source_records(p_source_id uuid)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, app_private, pg_temp
AS $$
DECLARE
  source_policy record;
  erased_count bigint;
  affected_cases uuid[];
BEGIN
  SELECT id, status, retention_restrictions INTO source_policy
  FROM app_private.source_catalog
  WHERE id = p_source_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'source catalog entry does not exist';
  END IF;
  IF source_policy.status <> 'suspended'
     OR source_policy.retention_restrictions <> 'delete_on_withdrawal' THEN
    RAISE EXCEPTION 'source must be suspended and require deletion on withdrawal';
  END IF;
  IF EXISTS (
    SELECT 1 FROM app_private.facility_evidence AS evidence
    JOIN app_private.source_records AS records ON records.id = evidence.source_record_id
    WHERE records.source_id = p_source_id
  ) OR EXISTS (
    SELECT 1 FROM app_private.facility_locations AS locations
    JOIN app_private.source_records AS records
      ON records.id = locations.coordinate_source_record_id
    WHERE records.source_id = p_source_id
  ) THEN
    RAISE EXCEPTION 'source snapshots are linked to published facility data; manual review required';
  END IF;

  SELECT array_agg(DISTINCT members.duplicate_case_id)
  INTO affected_cases
  FROM app_private.duplicate_case_candidates AS members
  JOIN app_private.candidate_records AS candidates
    ON candidates.id = members.candidate_record_id
  JOIN app_private.source_records AS records ON records.id = candidates.source_record_id
  WHERE records.source_id = p_source_id;

  PERFORM set_config('app.allow_source_erasure', 'true', true);
  DELETE FROM app_private.duplicate_cases
  WHERE id = ANY(COALESCE(affected_cases, ARRAY[]::uuid[]));
  DELETE FROM app_private.candidate_locations AS locations
  USING app_private.candidate_records AS candidates,
        app_private.source_records AS records
  WHERE locations.candidate_record_id = candidates.id
    AND candidates.source_record_id = records.id
    AND records.source_id = p_source_id;
  DELETE FROM app_private.candidate_evidence AS evidence
  USING app_private.source_records AS records
  WHERE evidence.source_record_id = records.id AND records.source_id = p_source_id;
  DELETE FROM app_private.etl_source_dispositions AS dispositions
  USING app_private.source_records AS records
  WHERE dispositions.source_record_id = records.id AND records.source_id = p_source_id;
  DELETE FROM app_private.candidate_records AS candidates
  USING app_private.source_records AS records
  WHERE candidates.source_record_id = records.id AND records.source_id = p_source_id;
  DELETE FROM app_private.source_records WHERE source_id = p_source_id;
  GET DIAGNOSTICS erased_count = ROW_COUNT;

  INSERT INTO app_private.audit_events (entity, entity_id, action, after_value)
  VALUES (
    'source_catalog', p_source_id, 'withdrawn_source_data_erased',
    jsonb_build_object('source_record_count', erased_count)
  );
  RETURN erased_count;
END;
$$;

REVOKE ALL ON FUNCTION app_private.erase_withdrawn_source_records(uuid) FROM PUBLIC;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_source_maintainer') THEN
    CREATE ROLE eye_source_maintainer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;
GRANT USAGE ON SCHEMA app_private TO eye_source_maintainer;
GRANT EXECUTE ON FUNCTION app_private.erase_withdrawn_source_records(uuid)
  TO eye_source_maintainer;

COMMIT;
