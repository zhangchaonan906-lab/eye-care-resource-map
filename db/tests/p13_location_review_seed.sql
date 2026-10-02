\set ON_ERROR_STOP on
BEGIN;
WITH target AS (
  SELECT cl.id
  FROM app_private.candidate_locations cl
  JOIN app_private.candidate_records c ON c.id=cl.candidate_record_id
  JOIN app_private.source_records sr ON sr.id=c.source_record_id
  JOIN app_private.source_catalog sc ON sc.id=sr.source_id
  WHERE sc.name='Fixture Directory' AND sr.source_key='clinic-001'
    AND cl.provider='fixture' AND cl.validation_status='verified'
  ORDER BY cl.created_at DESC,cl.id
  LIMIT 1
)
UPDATE app_private.candidate_locations cl
SET validation_status='needs_review',verified_at=NULL,error_code='LOW_PRECISION',
    validation_reason='P13 synthetic reviewer checkpoint'
FROM target WHERE cl.id=target.id;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM app_private.candidate_locations cl
    JOIN app_private.candidate_records c ON c.id=cl.candidate_record_id
    JOIN app_private.source_records sr ON sr.id=c.source_record_id
    WHERE sr.source_key='clinic-001' AND cl.provider='fixture'
      AND cl.validation_status='needs_review'
      AND cl.validation_reason='P13 synthetic reviewer checkpoint'
  ) THEN RAISE EXCEPTION 'P13 needs-review coordinate checkpoint was not created'; END IF;
END;
$$;
COMMIT;
