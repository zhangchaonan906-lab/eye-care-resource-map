import test from "node:test";
import assert from "node:assert/strict";
import { assertExplicitRestoreTarget, postgresEnvironment } from "../lib/database-admin.mjs";
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
