\set ON_ERROR_STOP on
SELECT format('CREATE ROLE eye_admin_review_runtime LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'admin_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eye_admin_review_runtime') \gexec
SELECT format('ALTER ROLE eye_admin_review_runtime WITH LOGIN INHERIT NOSUPERUSER NOCREATEROLE PASSWORD %L', :'admin_password') \gexec
GRANT CONNECT ON DATABASE eye TO eye_admin_review_runtime;
GRANT eye_admin_review TO eye_admin_review_runtime;
