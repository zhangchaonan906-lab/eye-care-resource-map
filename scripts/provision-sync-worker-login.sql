\set ON_ERROR_STOP on
\if :{?sync_password}
\else
  \echo 'sync_password psql variable is required'
  \quit 3
\endif
SELECT format('CREATE ROLE eye_sync_worker_runtime LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'sync_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eye_sync_worker_runtime') \gexec
SELECT format('ALTER ROLE eye_sync_worker_runtime WITH LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'sync_password') \gexec
GRANT CONNECT ON DATABASE eye TO eye_sync_worker_runtime;
GRANT eye_sync_worker TO eye_sync_worker_runtime;
