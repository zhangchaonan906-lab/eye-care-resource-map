\set ON_ERROR_STOP on
INSERT INTO app_private.source_catalog
  (name, url, use_basis, access_policy, status)
VALUES
  ('Legacy unknown access policy', 'https://legacy.invalid/unknown',
   'synthetic migration test', 'legacy-custom-value', 'pending'),
  ('Legacy null access policy', 'https://legacy.invalid/null',
   'synthetic migration test', NULL, 'pending'),
  ('Legacy manual access policy', 'https://legacy.invalid/manual',
   'synthetic migration test', 'manual_only', 'pending'),
  ('Legacy automated access policy', 'https://legacy.invalid/automated',
   'synthetic migration test', 'automated_access_allowed', 'pending');
