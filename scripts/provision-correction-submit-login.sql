\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eye_correction_runtime') THEN
    CREATE ROLE eye_correction_runtime LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
ALTER ROLE eye_correction_runtime WITH LOGIN INHERIT PASSWORD :'correction_password';
GRANT eye_correction_submit TO eye_correction_runtime;
GRANT CONNECT ON DATABASE eye TO eye_correction_runtime;
COMMIT;
