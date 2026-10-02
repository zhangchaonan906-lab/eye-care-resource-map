import { spawnSync } from "node:child_process";
import { chmodSync, mkdirSync, realpathSync, statSync, writeFileSync } from "node:fs";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { postgresEnvironment } from "./lib/database-admin.mjs";

const root = resolve(import.meta.dirname, "..");
if (!process.env.DATABASE_ADMIN_URL || !process.env.P14_BACKUP_DIR || !["local", "ci", "staging", "production"].includes(process.env.APP_ENV ?? "")) throw new Error("DATABASE_ADMIN_URL, P14_BACKUP_DIR, and a known APP_ENV are required");
const repository = realpathSync(root);
const requestedDirectory = resolve(process.env.P14_BACKUP_DIR);
function isInsideRepository(path) {
  const rel = relative(repository, path);
  return rel === "" || (!isAbsolute(rel) && rel !== ".." && !rel.startsWith(`..${sep}`));
}
if (isInsideRepository(requestedDirectory)) throw new Error("Refusing to store database backup inside repository");
mkdirSync(requestedDirectory, { recursive: true });
const directory = realpathSync(requestedDirectory);
if (isInsideRepository(directory)) throw new Error("Refusing to store database backup inside repository");
const git = spawnSync("git", ["rev-parse", "--short=12", "HEAD"], { cwd: root, encoding: "utf8" });
if (git.status !== 0) throw new Error("Unable to identify backup commit");
const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
const filename = `eye-map-${process.env.APP_ENV}-${stamp}-${git.stdout.trim()}.dump`;
const output = resolve(directory, filename);
const started = Date.now();
let result;
if (process.env.P14_PG_TOOL_CONTAINER) {
  result = spawnSync("docker", ["exec", process.env.P14_PG_TOOL_CONTAINER, "pg_dump", "--format=custom", "--no-owner", "--username", process.env.PGUSER ?? "eye", "--dbname", process.env.PGDATABASE ?? "eye"], { env: postgresEnvironment(process.env.DATABASE_ADMIN_URL), encoding: null, maxBuffer: 1024 * 1024 * 1024 });
  if (!result.error && result.status === 0) {
    writeFileSync(output, result.stdout, { mode: 0o600 });
  }
} else {
  result = spawnSync("pg_dump", ["--format=custom", "--no-owner", "--file", output], { env: postgresEnvironment(process.env.DATABASE_ADMIN_URL), encoding: "utf8" });
}
if (result.error || result.status !== 0) throw new Error("pg_dump failed; connection details suppressed");
chmodSync(output, 0o600);
console.log(JSON.stringify({ filename, sizeBytes: statSync(output).size, durationMs: Date.now() - started }));
