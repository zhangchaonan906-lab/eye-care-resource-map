\set ON_ERROR_STOP on
CREATE ROLE eye_etl_runtime LOGIN
  PASSWORD :'etl_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT;
GRANT eye_etl TO eye_etl_runtime;
