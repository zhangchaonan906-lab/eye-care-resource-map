\set ON_ERROR_STOP on
BEGIN;
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS app_private;
REVOKE ALL ON SCHEMA app_private FROM PUBLIC;
SET LOCAL search_path = app_private, public, extensions;

CREATE TABLE app_private.regions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  adcode text NOT NULL CHECK (adcode ~ '^[0-9]{6}$'),
  name text NOT NULL,
  level text NOT NULL CHECK (level IN ('province', 'city', 'district')),
  parent_id uuid REFERENCES app_private.regions(id),
  version text NOT NULL,
  valid_from date,
  valid_to date,
  UNIQUE (adcode, version),
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE app_private.organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL,
  registration_id text,
  ownership_type text CHECK (ownership_type IN ('public', 'private', 'unknown')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX organizations_registration_id_uq
  ON app_private.organizations (registration_id) WHERE registration_id IS NOT NULL;

CREATE TABLE app_private.source_catalog (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  url text NOT NULL CHECK (url ~ '^https://'),
  owner text,
  use_basis text NOT NULL,
  permitted_fields text[] NOT NULL DEFAULT '{}',
  access_policy text,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'suspended')),
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_private.facilities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid REFERENCES app_private.organizations(id),
  name text NOT NULL,
  normalized_name text NOT NULL,
  campus_name text,
  category text NOT NULL CHECK (category IN
    ('eye_specialty_hospital', 'general_hospital_ophthalmology',
     'ophthalmology_center', 'eye_clinic', 'unknown')),
  region_id uuid NOT NULL REFERENCES app_private.regions(id),
  address text NOT NULL,
  phone text,
  website text CHECK (website IS NULL OR website ~ '^https://'),
  hospital_level text,
  hospital_grade text,
  ophthalmology_status text NOT NULL DEFAULT 'unknown'
    CHECK (ophthalmology_status IN ('unknown', 'claimed', 'verified', 'rejected')),
  verification_status text NOT NULL DEFAULT 'candidate'
    CHECK (verification_status IN ('candidate', 'in_review', 'verified', 'published', 'withdrawn')),
  published_at timestamptz,
  last_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (verification_status <> 'published' OR published_at IS NOT NULL)
);
COMMIT;
