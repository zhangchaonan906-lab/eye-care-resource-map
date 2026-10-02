import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { verifyMigrationManifest } from "./lib/migration-manifest.mjs";
import { postgresEnvironment } from "./lib/database-admin.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
if (!process.env.DATABASE_ADMIN_URL) throw new Error("DATABASE_ADMIN_URL is required; connection values are never printed");
const env = postgresEnvironment(process.env.DATABASE_ADMIN_URL);
const manifest = verifyMigrationManifest({ migrationsDir: resolve(root, "db/migrations"), manifestPath: resolve(root, "db/migrations/manifest.json") });
function psql(args, input) {
  const toolContainer = process.env.P14_PG_TOOL_CONTAINER;
  const command = toolContainer ? "docker" : "psql";
  const commandArgs = toolContainer
    ? ["exec", "-i", toolContainer, "psql", "-X", "-h", "127.0.0.1", "-U", env.PGUSER, "-d", env.PGDATABASE, "-v", "ON_ERROR_STOP=1", ...args]
    : ["-X", "-v", "ON_ERROR_STOP=1", ...args];
  const result = spawnSync(command, commandArgs, { env, encoding: "utf8", input });
  if (result.error) throw new Error(`Could not run psql: ${result.error.message}`);
  if (result.status !== 0) {
    const diagnostic = result.stderr.trim();
    throw new Error(`Migration database command failed (exit ${result.status})${diagnostic ? `: ${diagnostic}` : ""}; connection details suppressed`);
  }
  return result.stdout.trim();
}
const state = psql(["-At", "-c", "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'app_private')::text || '|' || coalesce(to_regclass('public.schema_migrations')::text, '')"]);
const [hasAppSchema, registry] = state.split("|");
if (hasAppSchema === "true" && !registry) throw new Error("Existing application schema has no migration registry; refusing to guess its migration history");
psql(["-c", "CREATE TABLE IF NOT EXISTS public.schema_migrations (version text PRIMARY KEY CHECK (version ~ '^[0-9]{3}$'), filename text NOT NULL UNIQUE, checksum text NOT NULL CHECK (checksum ~ '^[a-f0-9]{64}$'), applied_at timestamptz NOT NULL DEFAULT now()); REVOKE ALL ON public.schema_migrations FROM PUBLIC;"]);
const appliedOutput = psql(["-At", "-F", "|", "-c", "SELECT version, filename, checksum FROM public.schema_migrations ORDER BY version"]);
const applied = appliedOutput ? appliedOutput.split(/\r?\n/).map((line) => line.split("|")) : [];
for (let index = 0; index < applied.length; index += 1) {
  const row = applied[index]; const expected = manifest.migrations[index];
  if (!expected || row[0] !== expected.version || row[1] !== expected.filename || row[2] !== expected.sha256) throw new Error(`Applied migration history drift at ${row[0]}; refusing to continue`);
}
for (const migration of manifest.migrations.slice(applied.length)) {
  let body = readFileSync(resolve(root, "db/migrations", migration.filename), "utf8");
  body = body.replace(/^(?:\\set ON_ERROR_STOP on\r?\n)?BEGIN;\s*/, "").replace(/\s*COMMIT;\s*$/, "");
  if (body === readFileSync(resolve(root, "db/migrations", migration.filename), "utf8")) throw new Error(`Migration ${migration.version} has no supported transaction wrapper`);
  const transaction = [
    "BEGIN;",
    "SELECT pg_advisory_xact_lock(hashtext('eye-care-resource-map-migrations'));",
    `SELECT NOT EXISTS (SELECT 1 FROM public.schema_migrations WHERE version = '${migration.version}') AS should_apply \\gset`,
    "\\if :should_apply",
    body,
    `INSERT INTO public.schema_migrations(version, filename, checksum) VALUES ('${migration.version}', '${migration.filename}', '${migration.sha256}');`,
    "\\endif",
    "COMMIT;",
  ].join("\n");
  psql([], transaction);
  console.log(`Applied migration ${migration.version} (${migration.filename})`);
  // Migration 009 updates the canonical P5 source catalog rows. Bootstrap
  // those reviewed catalog entries after their schema exists and before 009.
  if (migration.version === "008") {
    psql([], readFileSync(resolve(root, "scripts/seed-opendata-sources.sql"), "utf8"));
    console.log("Ensured reviewed P5 source catalog baseline is present.");
  }
}
console.log(`Migration state verified through ${manifest.maxVersion}; no connection details emitted.`);
