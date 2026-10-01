\set ON_ERROR_STOP on
\if :{?api_password}
\else
  \echo 'api_password psql variable is required'
  \quit 3
\endif
CREATE ROLE eye_public_api_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT PASSWORD :'api_password';
GRANT eye_public_api TO eye_public_api_runtime;
