\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
CREATE TABLE app_private.import_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id),
  region_code text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
  counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_summary text
);
CREATE TABLE app_private.source_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id),
  source_key text NOT NULL,
  raw_payload jsonb NOT NULL,
  source_url text NOT NULL CHECK (source_url ~ '^https://'),
  collected_at timestamptz NOT NULL DEFAULT now(),
  content_hash text NOT NULL CHECK (content_hash ~ '^[a-f0-9]{64}$'),
  import_run_id uuid NOT NULL REFERENCES app_private.import_runs(id),
  UNIQUE (source_id, source_key, content_hash)
);
CREATE TABLE app_private.candidate_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_record_id uuid NOT NULL UNIQUE REFERENCES app_private.source_records(id),
  parsed_fields jsonb NOT NULL,
  match_status text NOT NULL DEFAULT 'unmatched'
    CHECK (match_status IN ('unmatched', 'matched', 'needs_review', 'rejected')),
  proposed_facility_id uuid REFERENCES app_private.facilities(id)
);
CREATE TABLE app_private.facility_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id uuid NOT NULL REFERENCES app_private.facilities(id),
  source_record_id uuid NOT NULL REFERENCES app_private.source_records(id),
  field_name text NOT NULL,
  field_value jsonb NOT NULL,
  confidence numeric(3,2) CHECK (confidence BETWEEN 0 AND 1),
  reviewed_at timestamptz,
  UNIQUE (facility_id, source_record_id, field_name)
);
CREATE TABLE app_private.duplicate_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_ids uuid[] NOT NULL CHECK (cardinality(candidate_ids) >= 2),
  reason text NOT NULL,
  score numeric(3,2) CHECK (score BETWEEN 0 AND 1),
  resolution text NOT NULL DEFAULT 'pending'
    CHECK (resolution IN ('pending', 'merge', 'separate', 'reject')),
  reviewer_id uuid,
  resolved_at timestamptz
);
CREATE TABLE app_private.facility_locations (
  facility_id uuid PRIMARY KEY REFERENCES app_private.facilities(id) ON DELETE CASCADE,
  geog_wgs84 geography(Point, 4326) NOT NULL,
  coordinate_source_id uuid NOT NULL REFERENCES app_private.source_catalog(id),
  accuracy_m integer CHECK (accuracy_m IS NULL OR accuracy_m >= 0),
  location_status text NOT NULL DEFAULT 'candidate'
    CHECK (location_status IN ('candidate', 'verified', 'rejected')),
  verified_at timestamptz
);
CREATE TABLE app_private.audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid,
  entity text NOT NULL,
  entity_id uuid NOT NULL,
  action text NOT NULL,
  before_value jsonb,
  after_value jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
COMMIT;
