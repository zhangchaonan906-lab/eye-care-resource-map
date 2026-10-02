#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_name="eye-db-check-$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
backup_dir="$(mktemp -d "${TMPDIR:-/tmp}/eye-map-p14-backup.XXXXXX")"
random_secret() { python3 -c 'import secrets; print(secrets.token_hex(32))'; }
port="${EYE_MAP_DB_PORT:-$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')}"

export EYE_MAP_DB_PORT="$port"
export EYE_MAP_POSTGRES_PASSWORD="${EYE_MAP_POSTGRES_PASSWORD:-$(random_secret)}"
export P13_COLLECTOR_PASSWORD="$(random_secret)"
export P13_ETL_PASSWORD="$(random_secret)"
export P13_GEOCODE_PASSWORD="$(random_secret)"
export P13_PUBLIC_API_PASSWORD="$(random_secret)"
export P13_ADMIN_DATABASE_PASSWORD="$(random_secret)"
export P13_SYNC_PASSWORD="$(random_secret)"

export DATABASE_URL="postgresql://eye_collector_runtime:${P13_COLLECTOR_PASSWORD}@127.0.0.1:${port}/eye"
export ETL_DATABASE_URL="postgresql://eye_etl_runtime:${P13_ETL_PASSWORD}@127.0.0.1:${port}/eye"
export GEOCODE_DATABASE_URL="postgresql://eye_geocode_runtime:${P13_GEOCODE_PASSWORD}@127.0.0.1:${port}/eye"
export PUBLIC_API_DATABASE_URL="postgresql://eye_public_api_runtime:${P13_PUBLIC_API_PASSWORD}@127.0.0.1:${port}/eye"
export ADMIN_DATABASE_URL="postgresql://eye_admin_review_runtime:${P13_ADMIN_DATABASE_PASSWORD}@127.0.0.1:${port}/eye"
export SYNC_DATABASE_URL="postgresql://eye_sync_worker_runtime:${P13_SYNC_PASSWORD}@127.0.0.1:${port}/eye"
export DATABASE_ADMIN_URL="postgresql://eye:${EYE_MAP_POSTGRES_PASSWORD}@127.0.0.1:${port}/eye"

compose() { docker compose -p "$project_name" "$@"; }
cleanup() {
  local result=$?
  trap - EXIT
  compose down --volumes --remove-orphans || result=1
  rm -rf -- "$backup_dir"
  exit "$result"
}
trap cleanup EXIT

cd "$repo_root"
compose up -d --wait
node scripts/db-test-bootstrap.mjs "$project_name"
if ! command -v psql >/dev/null 2>&1; then echo 'psql client is required for the P14 migration runner test.' >&2; exit 1; fi
compose exec -T db createdb -U eye p14_migration_clean
compose exec -T db psql -h 127.0.0.1 -U eye -d p14_migration_clean -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION postgis WITH SCHEMA public'
migration_database_url="${DATABASE_ADMIN_URL%/eye}/p14_migration_clean"
DATABASE_ADMIN_URL="$migration_database_url" node scripts/apply-migrations.mjs
DATABASE_ADMIN_URL="$migration_database_url" node scripts/apply-migrations.mjs
migration_count="$(compose exec -T db psql -h 127.0.0.1 -U eye -d p14_migration_clean -A -t -c "SELECT count(*) FROM public.schema_migrations WHERE version BETWEEN '001' AND '015'" | tr -d '\r ' )"
test "$migration_count" = "15"

python3 -m pip install -e "services/collector[dev]"
(cd services/collector && python3 -m pytest -m database -q)
(cd services/collector && python3 -m eye_collector.cli run --source fixture --region 110000 >/dev/null)
(cd services/collector && python3 -m pytest -m etl_database -q)
(cd services/collector && python3 -m eye_collector.cli geocode --provider fixture --dry-run --limit 2 >/dev/null)
(cd services/collector && python3 -m pytest -m geocode_database -q)

(cd apps/web && npm ci --ignore-scripts && npm run test:db)

# Disposable P14 recovery drill with synthetic P1–P13 database content.
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/p14_restore_drill_seed.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -c "INSERT INTO app_private.audit_events(entity,entity_id,action) VALUES('p14_restore_drill',gen_random_uuid(),'synthetic_backup_drill')"
before="$(compose exec -T db psql -h 127.0.0.1 -U eye -d eye -A -t -F '|' -c "SELECT (SELECT count(*) FROM public.published_facility_api),(SELECT count(*) FROM app_private.audit_events),(SELECT count(*) FROM app_private.source_records),(SELECT count(*) FROM app_private.facility_locations),(SELECT count(*) FROM public.schema_migrations)" | tr -d '\r ' )"
if [[ "$before" == "0|0|0|0|0" ]]; then echo 'P14 restore drill needs non-empty synthetic fixtures.' >&2; exit 1; fi
export APP_ENV=ci P14_BACKUP_DIR="$backup_dir" P14_PG_TOOL_CONTAINER="$(compose ps -q db)"
node scripts/backup-db.mjs
backup_file="$(find "$backup_dir" -maxdepth 1 -name 'eye-map-ci-*.dump' -type f -print -quit)"
test -n "$backup_file"
restore_target="p14_restore_target"
compose exec -T db dropdb -U eye --if-exists "$restore_target"
compose exec -T db createdb -U eye --template=template0 "$restore_target"
restore_database_url="${DATABASE_ADMIN_URL%/eye}/$restore_target"
export RESTORE_DATABASE_URL="$restore_database_url" RESTORE_CONFIRM="$restore_target" RESTORE_BACKUP_FILE="$backup_file"
restore_started="$(date +%s)"
node scripts/restore-db.mjs
restore_duration=$(( $(date +%s) - restore_started ))
unset RESTORE_DATABASE_URL RESTORE_CONFIRM RESTORE_BACKUP_FILE P14_PG_TOOL_CONTAINER
after="$(compose exec -T db psql -h 127.0.0.1 -U eye -d "$restore_target" -A -t -F '|' -c "SELECT (SELECT count(*) FROM public.published_facility_api),(SELECT count(*) FROM app_private.audit_events),(SELECT count(*) FROM app_private.source_records),(SELECT count(*) FROM app_private.facility_locations),(SELECT count(*) FROM public.schema_migrations)" | tr -d '\r ' )"
test "$before" = "$after"
restored_public="$(compose exec -T db psql -q -h 127.0.0.1 -U eye -d "$restore_target" -A -t -c "SET ROLE eye_public_api_runtime; SELECT count(*) FROM public.query_published_facilities_bbox(116.3,39.8,116.5,40.0,NULL,NULL,NULL,10); RESET ROLE" | tr -d '\r ' )"
test "$restored_public" -gt 0
echo "P14 disposable backup/restore drill PASS; restore duration seconds: $restore_duration; restored counts: $after"
compose exec -T db dropdb -U eye "$restore_target"

if [[ -n "${P5_BEIJING_OFFICIAL_FILE:-}" && -n "${P5_SHENZHEN_OFFICIAL_FILE:-}" ]]; then
  (cd services/collector && python3 -m eye_collector.cli inspect-file --source beijing-open-data-designated-medical-institutions --file "$P5_BEIJING_OFFICIAL_FILE" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["row_count"]==4876 and d["schema_match"] and d["ready_to_import"]')
  (cd services/collector && python3 -m eye_collector.cli inspect-file --source shenzhen-open-data-baoan-hospital-basic-information --file "$P5_SHENZHEN_OFFICIAL_FILE" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["row_count"]==27 and d["schema_match"] and d["ready_to_import"]')
fi

echo 'P1–P14 disposable database checks passed.'
