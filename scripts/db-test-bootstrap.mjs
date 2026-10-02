import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const project = process.argv[2];
if (!project || !/^[a-z0-9][a-z0-9_-]{0,62}$/.test(project)) {
  throw new Error("Usage: node scripts/db-test-bootstrap.mjs <compose-project-name>");
}

const required = [
  "EYE_MAP_DB_PORT", "EYE_MAP_POSTGRES_PASSWORD", "P13_COLLECTOR_PASSWORD",
  "P13_ETL_PASSWORD", "P13_GEOCODE_PASSWORD", "P13_PUBLIC_API_PASSWORD",
  "P13_ADMIN_DATABASE_PASSWORD", "P13_SYNC_PASSWORD",
];
for (const name of required) {
  if (!process.env[name]) throw new Error(`${name} is required for disposable database bootstrap`);
}

function compose(...args) {
  const result = spawnSync("docker", ["compose", "-p", project, ...args], {
    cwd: root,
    stdio: "inherit",
    env: process.env,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`docker compose ${args[0]} failed with exit ${result.status}`);
}

function psql(file, variables = []) {
  compose("exec", "-T", "db", "psql", "-h", "127.0.0.1", "-U", "eye", "-d", "eye", "-v", "ON_ERROR_STOP=1", ...variables.flatMap((value) => ["-v", value]), "-f", file);
}

const migrations = [
  "/workspace/db/migrations/001_core.sql",
  "/workspace/db/migrations/002_evidence_location.sql",
  "/workspace/db/migrations/003_published_view.sql",
  "/workspace/db/migrations/004_collector_permissions.sql",
];
for (const file of migrations) psql(file);
psql("/workspace/db/tests/004_legacy_source_policy_fixture.sql");
psql("/workspace/db/migrations/005_etl_candidates.sql");
psql("/workspace/db/migrations/006_geocoding.sql");
psql("/workspace/db/migrations/007_source_open_data_rights.sql");
psql("/workspace/db/migrations/008_source_file_provenance.sql");
psql("/workspace/scripts/seed-opendata-sources.sql");
psql("/workspace/db/tests/009_real_export_compatibility_before.sql");
psql("/workspace/db/migrations/009_real_export_compatibility.sql");
psql("/workspace/db/migrations/010_etl_import_run_scope.sql");
for (const file of [
  "011_public_api.sql", "012_nearby_api.sql", "013_admin_review.sql",
  "014_incremental_sync.sql", "015_public_query_performance.sql",
]) psql(`/workspace/db/migrations/${file}`);

for (const [file, variable, value] of [
  ["provision-collector-login.sql", "collector_password", process.env.P13_COLLECTOR_PASSWORD],
  ["provision-etl-login.sql", "etl_password", process.env.P13_ETL_PASSWORD],
  ["provision-geocode-login.sql", "geocode_password", process.env.P13_GEOCODE_PASSWORD],
  ["provision-public-api-login.sql", "api_password", process.env.P13_PUBLIC_API_PASSWORD],
  ["provision-admin-review-login.sql", "admin_password", process.env.P13_ADMIN_DATABASE_PASSWORD],
  ["provision-sync-worker-login.sql", "sync_password", process.env.P13_SYNC_PASSWORD],
]) psql(`/workspace/scripts/${file}`, [`${variable}=${value}`]);

psql("/workspace/scripts/seed-fixture-source.sql");
for (const file of [
  "001_core.sql", "002_evidence_location.sql", "003_published_view.sql",
  "004_collector_permissions.sql", "005_etl_candidates.sql", "006_geocoding.sql",
  "007_source_open_data_rights.sql", "009_real_export_compatibility.sql",
  "011_public_api.sql", "012_nearby_api.sql", "013_admin_review.sql",
  "014_incremental_sync.sql", "p13_synthetic_performance.sql",
]) psql(`/workspace/db/tests/${file}`);

console.log("Disposable P1–P13 database bootstrap and regression SQL passed.");
