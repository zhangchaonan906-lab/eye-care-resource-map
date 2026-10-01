#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_name="eye-p5-check-$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
if [[ -z "${EYE_MAP_POSTGRES_PASSWORD:-}" ]]; then
  export EYE_MAP_POSTGRES_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
fi
if [[ -z "${EYE_MAP_DB_PORT:-}" ]]; then
  export EYE_MAP_DB_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
fi
collector_password="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
etl_password="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
geocode_password="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="postgresql://eye_collector_runtime:${collector_password}@127.0.0.1:${EYE_MAP_DB_PORT}/eye"
export ETL_DATABASE_URL="postgresql://eye_etl_runtime:${etl_password}@127.0.0.1:${EYE_MAP_DB_PORT}/eye"
export DATABASE_ADMIN_URL="postgresql://eye:${EYE_MAP_POSTGRES_PASSWORD}@127.0.0.1:${EYE_MAP_DB_PORT}/eye"
export GEOCODE_DATABASE_URL="postgresql://eye_geocode_runtime:${geocode_password}@127.0.0.1:${EYE_MAP_DB_PORT}/eye"

compose() {
  docker compose -p "$project_name" "$@"
}

cleanup() {
  local result=$?
  trap - EXIT
  compose down --volumes --remove-orphans || result=1
  exit "$result"
}
trap cleanup EXIT

compose up -d --wait
for sql_file in \
  /workspace/db/migrations/001_core.sql \
  /workspace/db/migrations/002_evidence_location.sql \
  /workspace/db/migrations/003_published_view.sql \
  /workspace/db/migrations/004_collector_permissions.sql; do
  compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f "$sql_file"
done
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/tests/004_legacy_source_policy_fixture.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/migrations/005_etl_candidates.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/migrations/006_geocoding.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/migrations/007_source_open_data_rights.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/migrations/008_source_file_provenance.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/scripts/seed-opendata-sources.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/tests/009_real_export_compatibility_before.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/db/migrations/009_real_export_compatibility.sql

for sql_file in \
  /workspace/db/tests/001_core.sql \
  /workspace/db/tests/002_evidence_location.sql \
  /workspace/db/tests/003_published_view.sql \
  /workspace/db/tests/004_collector_permissions.sql \
  /workspace/db/tests/005_etl_candidates.sql \
  /workspace/db/tests/006_geocoding.sql \
  /workspace/db/tests/007_source_open_data_rights.sql \
  /workspace/db/tests/009_real_export_compatibility.sql; do
  compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f "$sql_file"
done
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -v collector_password="$collector_password" -f /workspace/scripts/provision-collector-login.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -v etl_password="$etl_password" -f /workspace/scripts/provision-etl-login.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -v geocode_password="$geocode_password" -f /workspace/scripts/provision-geocode-login.sql
compose exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 \
  -f /workspace/scripts/seed-fixture-source.sql

cd "$repo_root/services/collector"
cli_result="$(python3 -m eye_collector.cli run --source fixture --region 110000 --dry-run --limit 1)"
printf '%s' "$cli_result" | python3 -c '
import json, sys
result = json.load(sys.stdin)
assert result["status"] == "succeeded"
assert result["dry_run"] is True
assert result["counts"]["inserted"] == 1
'
python3 -m pytest -m database -q
python3 -m eye_collector.cli run --source fixture --region 110000 >/dev/null
python3 -m pytest -m etl_database -q
geocode_cli_result="$(python3 -m eye_collector.cli geocode --provider fixture --dry-run --limit 2)"
printf '%s' "$geocode_cli_result" | python3 -c '
import json, sys
result = json.load(sys.stdin)
assert result["provider"] == "fixture"
assert result["dry_run"] is True
assert result["counts"]["candidates_read"] <= 2
'
python3 -m pytest -m geocode_database -q
