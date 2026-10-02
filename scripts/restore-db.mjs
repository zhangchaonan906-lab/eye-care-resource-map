import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { postgresEnvironment, assertExplicitRestoreTarget } from "./lib/database-admin.mjs";

if (!process.env.RESTORE_DATABASE_URL || !process.env.RESTORE_CONFIRM || !process.env.RESTORE_BACKUP_FILE) throw new Error("RESTORE_DATABASE_URL, RESTORE_CONFIRM, and RESTORE_BACKUP_FILE are required");
const target = decodeURIComponent(new URL(process.env.RESTORE_DATABASE_URL).pathname.slice(1));
assertExplicitRestoreTarget(target, process.env.RESTORE_CONFIRM);
const backup = resolve(process.env.RESTORE_BACKUP_FILE);
const env = postgresEnvironment(process.env.RESTORE_DATABASE_URL);
const isContainer = Boolean(process.env.P14_PG_TOOL_CONTAINER);
const psqlArgs = ["-At", "-U", env.PGUSER, "-d", target, "-c", "SELECT (SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('pg_catalog','information_schema','public') AND nspname NOT LIKE 'pg_toast%' AND nspname NOT LIKE 'pg_temp%') + (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','v','m','S','f','i','I','p'))"];
const contentCheck = isContainer
  ? spawnSync("docker", ["exec", process.env.P14_PG_TOOL_CONTAINER, "psql", ...psqlArgs], { env, encoding: "utf8" })
  : spawnSync("psql", ["-X", ...psqlArgs], { env, encoding: "utf8" });
if (contentCheck.error || contentCheck.status !== 0 || contentCheck.stdout.trim() !== "0") throw new Error("Restore target must be a new empty database (create it from template0); refusing to overwrite existing objects");
const useContainer = process.env.P14_PG_TOOL_CONTAINER;
const containerArchive = useContainer ? `/tmp/eye-map-restore-${randomUUID()}.dump` : undefined;
try {
  if (useContainer) {
    const copied = spawnSync("docker", ["cp", backup, `${useContainer}:${containerArchive}`], { encoding: "utf8" });
    if (copied.error || copied.status !== 0) throw new Error("Could not stage backup in PostgreSQL tool container");
  }
  const list = useContainer
    ? spawnSync("docker", ["exec", useContainer, "pg_restore", "--list", containerArchive], { env, encoding: "utf8", maxBuffer: 1024 * 1024 * 1024 })
    : spawnSync("pg_restore", ["--list", backup], { env, encoding: "utf8" });
  if (list.error || list.status !== 0) throw new Error("Backup is not a readable PostgreSQL custom-format archive");
  const started = Date.now();
  const restored = useContainer
    ? spawnSync("docker", ["exec", useContainer, "pg_restore", "--no-owner", "--username", env.PGUSER, "--dbname", target, containerArchive], { env, encoding: "utf8", maxBuffer: 1024 * 1024 * 1024 })
    : spawnSync("pg_restore", ["--no-owner", "--dbname", target, backup], { env, encoding: "utf8" });
  if (restored.error || restored.status !== 0) throw new Error("pg_restore failed; connection details suppressed");
  console.log(JSON.stringify({ targetDatabase: target, durationMs: Date.now() - started }));
} finally {
  if (useContainer && containerArchive) spawnSync("docker", ["exec", useContainer, "rm", "-f", containerArchive], { encoding: "utf8" });
}
