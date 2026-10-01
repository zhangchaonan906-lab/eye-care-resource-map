\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

-- P2 continues to use the exact automated_access_allowed value. Unknown legacy
-- values are converted to a blocked review state before constraining the column.
UPDATE app_private.source_catalog
SET access_policy = 'manual_review_required'
WHERE access_policy IS NULL
   OR access_policy NOT IN (
     'automated_access_allowed', 'manual_only', 'manual_review_required'
   );
ALTER TABLE app_private.source_catalog
  ALTER COLUMN access_policy SET DEFAULT 'manual_review_required',
  ALTER COLUMN access_policy SET NOT NULL,
  ADD CONSTRAINT source_catalog_access_policy_check
    CHECK (access_policy IN (
      'automated_access_allowed', 'manual_only', 'manual_review_required'
    )),
  ADD COLUMN registration_id_reliable boolean NOT NULL DEFAULT false;

ALTER TABLE app_private.candidate_records
  ADD COLUMN normalized_name text,
  ADD COLUMN normalized_address text,
  ADD COLUMN normalized_phone text,
  ADD COLUMN administrative_code text
    CHECK (administrative_code IS NULL OR administrative_code ~ '^[0-9]{6}$'),
  ADD COLUMN registration_id text,
  ADD COLUMN registration_id_reliable boolean NOT NULL DEFAULT false,
  ADD COLUMN campus_name text,
  ADD COLUMN pipeline_version text,
  ADD COLUMN processed_at timestamptz;

CREATE INDEX candidate_records_name_region_idx
  ON app_private.candidate_records (normalized_name, administrative_code)
  WHERE normalized_name IS NOT NULL AND administrative_code IS NOT NULL;
CREATE INDEX candidate_records_registration_idx
  ON app_private.candidate_records (registration_id)
  WHERE registration_id_reliable AND registration_id IS NOT NULL;

ALTER TABLE app_private.candidate_records
  ADD CONSTRAINT candidate_records_id_source_record_uq UNIQUE (id, source_record_id);

CREATE TABLE app_private.candidate_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_record_id uuid NOT NULL,
  source_record_id uuid NOT NULL,
  field_name text NOT NULL,
  evidence_value jsonb NOT NULL,
  evidence_text text NOT NULL,
  evidence_type text NOT NULL CHECK (evidence_type = 'explicit_field_mention'),
  rule_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (candidate_record_id, source_record_id)
    REFERENCES app_private.candidate_records(id, source_record_id) ON DELETE CASCADE,
  UNIQUE (candidate_record_id, field_name, evidence_text)
);

ALTER TABLE app_private.duplicate_cases
  ADD COLUMN match_fingerprint text;
CREATE UNIQUE INDEX duplicate_cases_match_fingerprint_uq
  ON app_private.duplicate_cases (match_fingerprint)
  WHERE match_fingerprint IS NOT NULL;

CREATE FUNCTION app_private.enforce_duplicate_case_min_members()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  target_case_id uuid;
BEGIN
  IF TG_TABLE_NAME = 'duplicate_cases' THEN
    IF TG_OP = 'DELETE' THEN
      target_case_id := OLD.id;
    ELSE
      target_case_id := NEW.id;
    END IF;
  ELSE
    IF TG_OP = 'DELETE' THEN
      target_case_id := OLD.duplicate_case_id;
    ELSE
      target_case_id := NEW.duplicate_case_id;
    END IF;
  END IF;

  IF EXISTS (
      SELECT 1 FROM app_private.duplicate_cases WHERE id = target_case_id
    ) AND (
      SELECT count(*) FROM app_private.duplicate_case_candidates
      WHERE duplicate_case_id = target_case_id
    ) < 2 THEN
    RAISE EXCEPTION 'duplicate case % must have at least two candidates', target_case_id
      USING ERRCODE = '23514';
  END IF;
  RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER duplicate_case_min_members_trg
AFTER INSERT OR UPDATE ON app_private.duplicate_cases
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION app_private.enforce_duplicate_case_min_members();

CREATE CONSTRAINT TRIGGER duplicate_case_candidate_min_members_trg
AFTER INSERT OR UPDATE OR DELETE ON app_private.duplicate_case_candidates
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION app_private.enforce_duplicate_case_min_members();

CREATE FUNCTION app_private.reject_source_record_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'source_records are immutable; insert a new snapshot instead'
    USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER source_records_immutable_trg
BEFORE UPDATE OR DELETE ON app_private.source_records
FOR EACH ROW EXECUTE FUNCTION app_private.reject_source_record_mutation();

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_etl') THEN
    CREATE ROLE eye_etl NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;

GRANT USAGE ON SCHEMA app_private TO eye_etl;
GRANT SELECT ON app_private.source_catalog TO eye_etl;
GRANT SELECT ON app_private.source_records TO eye_etl;
GRANT SELECT ON app_private.regions TO eye_etl;
GRANT SELECT ON app_private.organizations TO eye_etl;
GRANT SELECT ON app_private.facilities TO eye_etl;
GRANT SELECT ON app_private.candidate_records TO eye_etl;
GRANT INSERT (
  source_record_id, parsed_fields, normalized_name, normalized_address,
  normalized_phone, administrative_code, registration_id,
  registration_id_reliable, campus_name, pipeline_version, processed_at,
  match_status, proposed_facility_id
) ON app_private.candidate_records TO eye_etl;
GRANT UPDATE (match_status, proposed_facility_id)
  ON app_private.candidate_records TO eye_etl;
GRANT SELECT ON app_private.candidate_evidence TO eye_etl;
GRANT INSERT (
  candidate_record_id, source_record_id, field_name, evidence_value,
  evidence_text, evidence_type, rule_version
) ON app_private.candidate_evidence TO eye_etl;
GRANT SELECT ON app_private.duplicate_cases TO eye_etl;
GRANT INSERT (reason, match_fingerprint) ON app_private.duplicate_cases TO eye_etl;
GRANT SELECT ON app_private.duplicate_case_candidates TO eye_etl;
GRANT INSERT (duplicate_case_id, candidate_record_id)
  ON app_private.duplicate_case_candidates TO eye_etl;

COMMIT;
