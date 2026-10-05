import assert from "node:assert/strict";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { verifyMigrationManifest } from "../lib/migration-manifest.mjs";

const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const source = join(root, "db", "migrations");

test("migration inventory matches its ordered 001–016 SHA-256 manifest", () => {
  const result = verifyMigrationManifest({
    migrationsDir: source,
    manifestPath: join(source, "manifest.json"),
  });
  assert.equal(result.maxVersion, "016");
  assert.equal(result.migrations.length, 16);
  assert.equal(result.migrations[0].version, "001");
  assert.equal(result.migrations.at(-1).version, "016");
});

test("migration checksum drift fails closed", () => {
  const temporary = mkdtempSync(join(tmpdir(), "p14-migration-drift-"));
  try {
    const migrationsDir = join(temporary, "migrations");
    cpSync(source, migrationsDir, { recursive: true });
    const file = join(migrationsDir, "001_core.sql");
    writeFileSync(file, `${readFileSync(file, "utf8")}\n-- unregistered change\n`);
    assert.throws(() => verifyMigrationManifest({ migrationsDir, manifestPath: join(migrationsDir, "manifest.json") }), /checksum mismatch/i);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});

test("migration checksum is stable across Windows and Unix line endings", () => {
  const temporary = mkdtempSync(join(tmpdir(), "p14-migration-eol-"));
  try {
    const migrationsDir = join(temporary, "migrations");
    cpSync(source, migrationsDir, { recursive: true });
    const file = join(migrationsDir, "001_core.sql");
    const unixText = readFileSync(file, "utf8").replace(/\r\n?/g, "\n");
    writeFileSync(file, unixText.replace(/\n/g, "\r\n"));
    assert.equal(verifyMigrationManifest({ migrationsDir, manifestPath: join(migrationsDir, "manifest.json") }).maxVersion, "016");
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});

test("unexpected migration files fail closed", () => {
  const temporary = mkdtempSync(join(tmpdir(), "p14-migration-extra-"));
  try {
    const migrationsDir = join(temporary, "migrations");
    cpSync(source, migrationsDir, { recursive: true });
    writeFileSync(join(migrationsDir, "016_untracked.sql"), "SELECT 1;\n");
    assert.throws(() => verifyMigrationManifest({ migrationsDir, manifestPath: join(migrationsDir, "manifest.json") }), /inventory mismatch/i);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
