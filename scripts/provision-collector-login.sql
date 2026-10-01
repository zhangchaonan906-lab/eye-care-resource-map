\set ON_ERROR_STOP on
CREATE ROLE eye_collector_runtime LOGIN
  PASSWORD :'collector_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT;
GRANT eye_collector TO eye_collector_runtime;
