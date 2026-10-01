\set ON_ERROR_STOP on
CREATE ROLE eye_geocode_runtime LOGIN
  PASSWORD :'geocode_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT;
GRANT eye_geocode TO eye_geocode_runtime;
