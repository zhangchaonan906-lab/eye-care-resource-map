import { Pool } from "pg";

const NO_STORE = { "Cache-Control": "no-store" };

export function liveResponse(): Response {
  return Response.json({ status: "ok" }, { status: 200, headers: NO_STORE });
}

export async function readyResponse(probe: () => Promise<unknown>): Promise<Response> {
  try {
    await probe();
    return Response.json({ status: "ok" }, { status: 200, headers: NO_STORE });
  } catch {
    return Response.json({ status: "unavailable" }, { status: 503, headers: NO_STORE });
  }
}

export function versionResponse(env: Record<string, string | undefined> = process.env): Response {
  const commitInput = env.RELEASE_COMMIT_SHA ?? env.VERCEL_GIT_COMMIT_SHA ?? env.GITHUB_SHA ?? "";
  const commit = /^[\da-f]{7,40}$/i.test(commitInput) ? commitInput.toLowerCase() : "unknown";
  const timestamp = env.BUILD_TIMESTAMP ?? "";
  const parsedTimestamp = timestamp ? Date.parse(timestamp) : Number.NaN;
  const buildTime = Number.isFinite(parsedTimestamp) ? new Date(parsedTimestamp).toISOString() : "unknown";
  const environment = ["local", "ci", "staging", "production"].includes(env.APP_ENV ?? "")
    ? env.APP_ENV!
    : "unknown";
  return Response.json({ commit, buildTime, environment }, { status: 200, headers: NO_STORE });
}

let readinessPool: Pool | undefined;

async function probePublicDatabase(): Promise<void> {
  const connectionString = process.env.PUBLIC_API_DATABASE_URL;
  if (!connectionString) throw new Error("readiness database unavailable");
  readinessPool ??= new Pool({
    connectionString,
    max: 1,
    connectionTimeoutMillis: 3_000,
    idleTimeoutMillis: 10_000,
    allowExitOnIdle: true,
  });
  await readinessPool.query("SELECT 1");
}

export function publicDatabaseReadiness(): Promise<Response> {
  return readyResponse(probePublicDatabase);
}
