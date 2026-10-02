#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_name="eye-db-check-$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
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
  exit "$result"
}
trap cleanup EXIT

cd "$repo_root"
compose up -d --wait
node scripts/db-test-bootstrap.mjs "$project_name"

python3 -m pip install -e "services/collector[dev]"
(cd services/collector && python3 -m pytest -m database -q)
(cd services/collector && python3 -m eye_collector.cli run --source fixture --region 110000 >/dev/null)
(cd services/collector && python3 -m pytest -m etl_database -q)
(cd services/collector && python3 -m eye_collector.cli geocode --provider fixture --dry-run --limit 2 >/dev/null)
(cd services/collector && python3 -m pytest -m geocode_database -q)

(cd apps/web && npm ci --ignore-scripts && npm run test:db)

if [[ -n "${P5_BEIJING_OFFICIAL_FILE:-}" && -n "${P5_SHENZHEN_OFFICIAL_FILE:-}" ]]; then
  (cd services/collector && python3 -m eye_collector.cli inspect-file --source beijing-open-data-designated-medical-institutions --file "$P5_BEIJING_OFFICIAL_FILE" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["row_count"]==4876 and d["schema_match"] and d["ready_to_import"]')
  (cd services/collector && python3 -m eye_collector.cli inspect-file --source shenzhen-open-data-baoan-hospital-basic-information --file "$P5_SHENZHEN_OFFICIAL_FILE" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["row_count"]==27 and d["schema_match"] and d["ready_to_import"]')
fi

echo 'P1–P13 disposable database checks passed.'
