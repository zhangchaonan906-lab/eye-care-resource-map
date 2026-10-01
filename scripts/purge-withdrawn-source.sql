\set ON_ERROR_STOP on
BEGIN;

UPDATE app_private.source_catalog
SET status = 'suspended'
WHERE id = :'source_id'::uuid
  AND retention_restrictions = 'delete_on_withdrawal';

SELECT app_private.erase_withdrawn_source_records(:'source_id'::uuid)
  AS erased_source_records;

COMMIT;
