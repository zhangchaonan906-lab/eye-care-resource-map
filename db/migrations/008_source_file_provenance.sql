\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

ALTER TABLE app_private.import_runs
  ADD COLUMN file_original_filename text,
  ADD COLUMN file_sha256 text,
  ADD COLUMN file_size_bytes bigint,
  ADD COLUMN file_obtained_at timestamptz,
  ADD COLUMN file_dataset_page text,
  ADD COLUMN file_source_updated_at date,
  ADD COLUMN file_operator text,
  ADD COLUMN file_acquisition_method text,
  ADD CONSTRAINT import_runs_file_provenance_complete CHECK (
    (
      file_original_filename IS NULL
      AND file_sha256 IS NULL
      AND file_size_bytes IS NULL
      AND file_obtained_at IS NULL
      AND file_dataset_page IS NULL
      AND file_source_updated_at IS NULL
      AND file_operator IS NULL
      AND file_acquisition_method IS NULL
    )
    OR (
      file_original_filename IS NOT NULL
      AND file_original_filename <> ''
      AND position('/' IN file_original_filename) = 0
      AND position(chr(92) IN file_original_filename) = 0
      AND file_sha256 IS NOT NULL
      AND file_sha256 ~ '^[0-9a-f]{64}$'
      AND file_size_bytes IS NOT NULL
      AND file_size_bytes > 0
      AND file_obtained_at IS NOT NULL
      AND file_dataset_page IS NOT NULL
      AND file_dataset_page ~ '^https://'
      AND file_operator IS NOT NULL
      AND btrim(file_operator) <> ''
      AND file_acquisition_method IS NOT NULL
      AND file_acquisition_method = 'official_portal_manual_download'
    )
  );

GRANT SELECT (dataset_page, source_updated_at, pilot_group, pilot_group_record_limit)
  ON app_private.source_catalog TO eye_collector;
GRANT INSERT (
  source_id, region_code, status, file_original_filename, file_sha256,
  file_size_bytes, file_obtained_at, file_dataset_page, file_source_updated_at,
  file_operator, file_acquisition_method
) ON app_private.import_runs TO eye_collector;

COMMIT;
