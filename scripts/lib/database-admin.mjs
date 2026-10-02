import { URL } from "node:url";

export function postgresEnvironment(connectionString) {
  const url = new URL(connectionString);
  if (!["postgres:", "postgresql:"].includes(url.protocol)) throw new Error("DATABASE_ADMIN_URL must use PostgreSQL");
  const database = decodeURIComponent(url.pathname.slice(1));
  if (!database || !url.hostname) throw new Error("DATABASE_ADMIN_URL must identify a database");
  const env = { ...process.env, PGHOST: url.hostname, PGPORT: url.port || "5432", PGDATABASE: database,
    PGUSER: decodeURIComponent(url.username), PGPASSWORD: decodeURIComponent(url.password),
    PGSSLMODE: url.searchParams.get("sslmode") || "prefer" };
  delete env.DATABASE_ADMIN_URL;
  delete env.DATABASE_URL;
  return env;
}

export function assertExplicitRestoreTarget(target, confirmation) {
  if (!target || target !== confirmation) throw new Error("RESTORE_CONFIRM must exactly match the explicit target database name");
  if (/(^|[-_])(prod|production)([-_]|$)/i.test(target)) throw new Error("Refusing to restore into a production-like database");
}
