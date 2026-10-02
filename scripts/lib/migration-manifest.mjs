import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { basename, join } from "node:path";

export function verifyMigrationManifest({ migrationsDir, manifestPath }) {
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  if (manifest.formatVersion !== 1 || !/^\d{3}$/.test(manifest.maxVersion) || !Array.isArray(manifest.migrations)) {
    throw new Error("Invalid migration manifest format");
  }

  const expectedCount = Number(manifest.maxVersion);
  if (manifest.migrations.length !== expectedCount) throw new Error("Migration inventory mismatch: non-contiguous version range");
  const actualFilenames = readdirSync(migrationsDir).filter((name) => name.endsWith(".sql")).sort();
  const manifestFilenames = [];

  for (let index = 0; index < manifest.migrations.length; index += 1) {
    const migration = manifest.migrations[index];
    const expectedVersion = String(index + 1).padStart(3, "0");
    if (migration.version !== expectedVersion) throw new Error(`Migration inventory mismatch: expected version ${expectedVersion}`);
    if (basename(migration.filename) !== migration.filename || !new RegExp(`^${expectedVersion}_[a-z0-9_]+\\.sql$`).test(migration.filename)) {
      throw new Error(`Invalid migration filename for version ${expectedVersion}`);
    }
    if (!/^[a-f0-9]{64}$/.test(migration.sha256)) throw new Error(`Invalid SHA-256 checksum for version ${expectedVersion}`);
    manifestFilenames.push(migration.filename);
  }

  if (JSON.stringify(actualFilenames) !== JSON.stringify(manifestFilenames)) {
    throw new Error("Migration inventory mismatch: SQL files differ from the manifest");
  }

  for (const migration of manifest.migrations) {
    // Git may check these SQL text files out with CRLF on Windows. Hash the
    // canonical repository text (LF) so CI and local verification agree.
    const sql = readFileSync(join(migrationsDir, migration.filename), "utf8").replace(/\r\n?/g, "\n");
    const actual = createHash("sha256").update(sql, "utf8").digest("hex");
    if (actual !== migration.sha256) throw new Error(`Migration checksum mismatch: ${migration.filename}`);
  }

  if (manifest.migrations.at(-1)?.version !== manifest.maxVersion) throw new Error("Migration maxVersion does not match the last entry");
  return manifest;
}
