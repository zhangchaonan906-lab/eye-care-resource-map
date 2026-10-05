import { randomBytes, randomUUID, scryptSync } from "node:crypto";
import { spawnSync } from "node:child_process";
import net from "node:net";
import { resolve } from "node:path";
import { rmSync } from "node:fs";

const root = resolve(import.meta.dirname, "..");
const project = `eye-p13-system-${randomBytes(4).toString("hex")}`;
const collector = resolve(root, "services/collector");
const web = resolve(root, "apps/web");

function secret() { return randomBytes(32).toString("hex"); }

async function freePort() {
  const server = net.createServer();
  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Could not allocate an isolated test database port");
  await new Promise((resolveClose, reject) => server.close((error) => error ? reject(error) : resolveClose()));
  return address.port;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? root,
    env: process.env,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error) throw result.error;
  if (result.status !== 0 && !options.allowFailure) {
    throw new Error(`${command} ${args[0] ?? ""} failed with exit ${result.status}`);
  }
  return result;
}

function compose(...args) { return run("docker", ["compose", "-p", project, ...args]); }

function psql(file) {
  compose("exec", "-T", "db", "psql", "-h", "127.0.0.1", "-U", "eye", "-d", "eye", "-v", "ON_ERROR_STOP=1", "-f", file);
}

function scalar(sql) {
  const result = run("docker", ["compose", "-p", project, "exec", "-T", "db", "psql", "-h", "127.0.0.1", "-U", "eye", "-d", "eye", "-A", "-t", "-c", sql]);
  return result.stdout.trim();
}

function python() { return process.platform === "win32" ? "py" : "python3"; }

function provisionAppAuth() {
  const password = `P13-System-${secret()}`;
  const salt = randomBytes(16);
  const digest = scryptSync(password, salt, 64, { N: 16_384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
  process.env.ADMIN_USERNAME = "p13-system-reviewer";
  process.env.P13_ADMIN_PASSWORD = password;
  process.env.ADMIN_PASSWORD_HASH = `scrypt$16384$8$1$${salt.toString("base64url")}$${digest.toString("base64url")}`;
  process.env.ADMIN_SESSION_SECRET = secret();
  process.env.ADMIN_ACTOR_ID = randomUUID();
}

function configureDatabase(passwords, port, webPort) {
  process.env.EYE_MAP_DB_PORT = String(port);
  process.env.EYE_MAP_POSTGRES_PASSWORD = passwords.root;
  process.env.P13_COLLECTOR_PASSWORD = passwords.collector;
  process.env.P13_ETL_PASSWORD = passwords.etl;
  process.env.P13_GEOCODE_PASSWORD = passwords.geocode;
  process.env.P13_PUBLIC_API_PASSWORD = passwords.publicApi;
  process.env.P13_ADMIN_DATABASE_PASSWORD = passwords.admin;
  process.env.P13_SYNC_PASSWORD = passwords.sync;
  process.env.P13_CORRECTION_PASSWORD = passwords.correction;
  process.env.DATABASE_URL = `postgresql://eye_collector_runtime:${passwords.collector}@127.0.0.1:${port}/eye`;
  process.env.ETL_DATABASE_URL = `postgresql://eye_etl_runtime:${passwords.etl}@127.0.0.1:${port}/eye`;
  process.env.GEOCODE_DATABASE_URL = `postgresql://eye_geocode_runtime:${passwords.geocode}@127.0.0.1:${port}/eye`;
  process.env.PUBLIC_API_DATABASE_URL = `postgresql://eye_public_api_runtime:${passwords.publicApi}@127.0.0.1:${port}/eye`;
  process.env.ADMIN_DATABASE_URL = `postgresql://eye_admin_review_runtime:${passwords.admin}@127.0.0.1:${port}/eye`;
  process.env.SYNC_DATABASE_URL = `postgresql://eye_sync_worker_runtime:${passwords.sync}@127.0.0.1:${port}/eye`;
  process.env.CORRECTION_DATABASE_URL = `postgresql://eye_correction_runtime:${passwords.correction}@127.0.0.1:${port}/eye`;
  process.env.DATABASE_ADMIN_URL = `postgresql://eye:${passwords.root}@127.0.0.1:${port}/eye`;
  process.env.NEXT_TELEMETRY_DISABLED = "1";
  process.env.PLAYWRIGHT_PORT = String(webPort);
  process.env.P13_SYSTEM_TEST_MODE = "true";
  process.env.APP_ENV = "staging";
  process.env.TRUST_PROXY_HEADERS = "true";
  process.env.RATE_LIMIT_HASH_SECRET = secret();
  process.env.RELEASE_COMMIT_SHA = run("git", ["rev-parse", "HEAD"]).stdout.trim();
  process.env.BUILD_TIMESTAMP = new Date().toISOString();
}

async function main() {
  const port = await freePort();
  const webPort = await freePort();
  configureDatabase({ root: secret(), collector: secret(), etl: secret(), geocode: secret(), publicApi: secret(), admin: secret(), sync: secret(), correction: secret() }, port, webPort);
  provisionAppAuth();
  let databaseStarted = false;
  try {
    databaseStarted = true;
    compose("up", "-d", "--wait");
    run(process.execPath, ["scripts/db-test-bootstrap.mjs", project]);
    psql("/workspace/db/tests/p13_system_seed.sql");

    process.stdout.write("P13 system setup: run the real scheduler and fixture worker.\n");
    const scheduler = run(python(), ["-m", "eye_collector.cli", "scheduler", "--once"], { cwd: collector });
    if (!scheduler.stdout.includes('"queued":1')) throw new Error("P13 scheduler did not queue exactly one durable fixture task");
    run(python(), ["-m", "eye_collector.cli", "worker", "--once", "--worker-id", "p13-stable-fixture"], { cwd: collector });
    const terminal = scalar("SELECT count(*) FROM app_private.source_sync_tasks WHERE status='succeeded' AND adapter_key='fixture'");
    const snapshots = scalar("SELECT count(*) FROM app_private.source_records sr JOIN app_private.source_catalog sc ON sc.id=sr.source_id WHERE sc.name='Fixture Directory'");
    const candidates = scalar("SELECT count(*) FROM app_private.candidate_records c JOIN app_private.source_records sr ON sr.id=c.source_record_id JOIN app_private.source_catalog sc ON sc.id=sr.source_id WHERE sc.name='Fixture Directory'");
    const duplicates = scalar("SELECT count(*) FROM app_private.duplicate_cases dc WHERE dc.resolution='pending' AND (SELECT count(*) FROM app_private.duplicate_case_candidates m WHERE m.duplicate_case_id=dc.id)>=2");
    if (terminal !== "1" || Number(snapshots) < 5 || Number(candidates) < 4 || Number(duplicates) < 1) {
      throw new Error(`P13 real worker setup incomplete: succeeded=${terminal}, snapshots=${snapshots}, candidates=${candidates}, pendingDuplicates=${duplicates}`);
    }

    run(python(), ["-m", "eye_collector.cli", "geocode", "--provider", "fixture", "--limit", "100"], { cwd: collector });
    psql("/workspace/db/tests/p13_location_review_seed.sql");
    const locations = scalar("SELECT count(*) FROM app_private.candidate_locations WHERE provider='fixture' AND longitude_wgs84 IS NOT NULL");
    if (Number(locations) < 3) throw new Error("Persistent fixture candidate locations were not created");

    const ids = scalar(`SELECT
      (SELECT c.id FROM app_private.candidate_records c JOIN app_private.source_records sr ON sr.id=c.source_record_id WHERE sr.source_key='clinic-001' ORDER BY sr.collected_at LIMIT 1),
      (SELECT dc.id FROM app_private.duplicate_cases dc JOIN app_private.duplicate_case_candidates m ON m.duplicate_case_id=dc.id JOIN app_private.candidate_records c ON c.id=m.candidate_record_id JOIN app_private.source_records sr ON sr.id=c.source_record_id WHERE dc.resolution='pending' AND sr.source_key IN ('clinic-001','clinic-002') GROUP BY dc.id HAVING count(DISTINCT sr.source_key)=2 ORDER BY dc.id LIMIT 1),
      (SELECT cl.id FROM app_private.candidate_locations cl JOIN app_private.candidate_records c ON c.id=cl.candidate_record_id JOIN app_private.source_records sr ON sr.id=c.source_record_id WHERE sr.source_key='clinic-001' AND cl.provider='fixture' AND cl.longitude_wgs84 IS NOT NULL ORDER BY cl.created_at LIMIT 1),
      (SELECT c.id FROM app_private.candidate_records c JOIN app_private.source_records sr ON sr.id=c.source_record_id WHERE sr.source_key='clinic-006' ORDER BY sr.collected_at LIMIT 1)`);
    const [candidateId, duplicateId, locationId, alternativeCandidateId] = ids.split("|");
    if (![candidateId, duplicateId, locationId, alternativeCandidateId].every((value) => /^[0-9a-f-]{36}$/i.test(value ?? ""))) {
      throw new Error("P13 fixture candidate, duplicate, or location identifiers were not seeded");
    }
    process.env.P13_CANDIDATE_ID = candidateId;
    process.env.P13_DUPLICATE_CASE_ID = duplicateId;
    process.env.P13_LOCATION_ID = locationId;
    process.env.P13_ALTERNATIVE_CANDIDATE_ID = alternativeCandidateId;

    process.stdout.write("P13 system setup: verify retry and two-source worker isolation.\n");
    run(python(), ["-m", "pytest", "tests/system/test_failure_isolation.py", "-q"], { cwd: collector });
    psql("/workspace/db/tests/p13_seed_500_facilities.sql");
    const stressRows = scalar("SELECT count(*) FROM app_private.facilities WHERE normalized_name LIKE 'p13 synthetic stress hospital %' AND verification_status='published'");
    if (stressRows !== "500") throw new Error(`Expected exactly 500 published synthetic stress facilities; got ${stressRows}`);
    process.env.P13_STRESS_FACILITY_ID = scalar("SELECT id FROM app_private.facilities WHERE normalized_name='p13 synthetic stress hospital 0001'");
    if (!/^[0-9a-f-]{36}$/i.test(process.env.P13_STRESS_FACILITY_ID)) throw new Error("Synthetic stress deep-link facility was not created");

    process.stdout.write("P13 system setup: build Next.js with real disposable DB roles.\n");
    run(process.execPath, ["scripts/copy-maplibre-worker.mjs"], { cwd: web });
    run(process.execPath, [resolve(web, "node_modules/next/dist/bin/next"), "build"], { cwd: web });
    process.stdout.write("P13 system verification: Chromium browser to real Next routes to disposable PostgreSQL.\n");
    rmSync(resolve(web, "test-results"), { recursive: true, force: true });
    const playwright = run(process.execPath, [resolve(web, "node_modules/playwright/cli.js"), "test", "--config", "playwright.system.config.ts"], { cwd: web, allowFailure: true });
    const scanner = run(python(), ["scripts/scan-playwright-artifacts.py"], { cwd: web, allowFailure: true });
    if (scanner.status !== 0) throw new Error("P13 system browser artifacts failed the dynamic secret scan");
    if (playwright.status !== 0) throw new Error(`P13 real system Playwright suite failed with exit ${playwright.status}`);
  } finally {
    if (databaseStarted) compose("down", "--volumes", "--remove-orphans");
    for (const name of [
      "EYE_MAP_DB_PORT", "EYE_MAP_POSTGRES_PASSWORD", "P13_COLLECTOR_PASSWORD", "P13_ETL_PASSWORD",
      "P13_GEOCODE_PASSWORD", "P13_PUBLIC_API_PASSWORD", "P13_ADMIN_DATABASE_PASSWORD", "P13_SYNC_PASSWORD",
      "DATABASE_URL", "ETL_DATABASE_URL", "GEOCODE_DATABASE_URL", "PUBLIC_API_DATABASE_URL",
      "ADMIN_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_ADMIN_URL", "ADMIN_USERNAME",
      "P13_ADMIN_PASSWORD", "ADMIN_PASSWORD_HASH", "ADMIN_SESSION_SECRET", "ADMIN_ACTOR_ID",
      "NEXT_TELEMETRY_DISABLED", "PLAYWRIGHT_PORT", "P13_SYSTEM_TEST_MODE", "P13_CANDIDATE_ID",
      "APP_ENV", "SITE_URL", "RELEASE_COMMIT_SHA", "BUILD_TIMESTAMP",
      "CORRECTION_DATABASE_URL", "P13_CORRECTION_PASSWORD", "TRUST_PROXY_HEADERS", "RATE_LIMIT_HASH_SECRET",
      "P13_DUPLICATE_CASE_ID", "P13_LOCATION_ID", "P13_ALTERNATIVE_CANDIDATE_ID",
      "P13_STRESS_FACILITY_ID",
    ]) delete process.env[name];
  }
}

await main();
