import test from "node:test";
import assert from "node:assert/strict";
import { assertExplicitRestoreTarget, postgresEnvironment } from "../lib/database-admin.mjs";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { validateReleaseGateManifest } from "../lib/release-gates.mjs";
test("admin URL becomes a psql environment without retaining URL variables", () => {
  const env = postgresEnvironment("postgresql://operator:p%40ss@db.example:5433/staging?sslmode=require");
  assert.equal(env.PGHOST, "db.example"); assert.equal(env.PGPASSWORD, "p@ss"); assert.equal(env.PGDATABASE, "staging"); assert.equal(env.PGSSLMODE, "require");
  assert.equal("DATABASE_ADMIN_URL" in env, false); assert.equal("DATABASE_URL" in env, false);
});
test("restore confirmation and production-like target fail closed", () => {
  assert.throws(() => assertExplicitRestoreTarget("staging_restore", "wrong"), /exactly match/);
  assert.throws(() => assertExplicitRestoreTarget("production", "production"), /production-like/);
  assert.doesNotThrow(() => assertExplicitRestoreTarget("restore_drill", "restore_drill"));
});
test("release gate manifest requires complete, valid evidence metadata", () => {
  const manifest = JSON.parse(readFileSync(resolve(import.meta.dirname, "../../docs/operations/p14-release-gates.json"), "utf8"));
  assert.deepEqual(validateReleaseGateManifest(manifest), []);
});
test("release gate manifest rejects missing metadata and invalid timestamps", () => {
  const manifest = { gates: { EXAMPLE: { status: "PASS", owner: "release", evidence: "checked", requiredAction: "none", verifiedAt: "yesterday" } } };
  const errors = validateReleaseGateManifest(manifest);
  assert.ok(errors.some((error) => error.includes("verifiedAt")));
  delete manifest.gates.EXAMPLE.owner;
  assert.ok(validateReleaseGateManifest(manifest).some((error) => error.includes("missing owner")));
});
test("production release guard remains fail-closed while mandatory gates are pending", () => {
  const result = spawnSync(process.execPath, [resolve(import.meta.dirname, "../check-production-release.mjs")], { encoding: "utf8" });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /STAGING_DATABASE=PENDING/);
  assert.match(result.stderr, /REAL_PUBLISHED_DATA_SAMPLE=PENDING/);
});
