\set ON_ERROR_STOP on
INSERT INTO app_private.source_catalog
  (name, url, owner, use_basis, permitted_fields, access_policy, status, reviewed_at,
   registration_id_reliable)
SELECT
  'Fixture Directory',
  'https://fixture.invalid/directory',
  'Local synthetic fixture',
  'Synthetic packaged test data only; no external source or collection rights asserted',
  ARRAY['name', 'address', 'phone', 'region', 'administrative_code',
    'registration_id', 'campus_name', 'departments', 'updated_at'],
  'automated_access_allowed',
  'approved',
  now(),
  true
WHERE NOT EXISTS (
  SELECT 1 FROM app_private.source_catalog
  WHERE name = 'Fixture Directory' AND url = 'https://fixture.invalid/directory'
);

UPDATE app_private.source_catalog
SET registration_id_reliable = true,
    permitted_fields = ARRAY['name', 'address', 'phone', 'region', 'administrative_code',
      'registration_id', 'campus_name', 'departments', 'updated_at']
WHERE name = 'Fixture Directory' AND url = 'https://fixture.invalid/directory';

INSERT INTO app_private.source_catalog
  (name, url, owner, use_basis, permitted_fields, access_policy, status, reviewed_at)
SELECT name, url, 'Local test', use_basis, ARRAY['name'], access_policy, status, now()
FROM (VALUES
  ('Fixture Pending Directory', 'https://fixture.invalid/pending',
   'Synthetic approval-gate test', 'automated_access_allowed', 'pending'),
  ('Fixture Suspended Directory', 'https://fixture.invalid/suspended',
   'Synthetic approval-gate test', 'automated_access_allowed', 'suspended'),
  ('Fixture Blocked Directory', 'https://fixture.invalid/blocked',
   'Synthetic access-policy test', 'manual_only', 'approved')
) AS fixtures(name, url, use_basis, access_policy, status)
WHERE NOT EXISTS (
  SELECT 1 FROM app_private.source_catalog sc
  WHERE sc.name = fixtures.name AND sc.url = fixtures.url
);
