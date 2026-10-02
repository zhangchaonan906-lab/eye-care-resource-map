import { describe, expect, it } from "vitest";
import { liveResponse, readyResponse, versionResponse } from "./endpoints";

describe("release endpoints", () => {
  it("returns a database-independent liveness response", async () => {
    const response = liveResponse();
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({ status: "ok" });
  });

  it("returns only a generic readiness status when the database probe succeeds or fails", async () => {
    const success = await readyResponse(async () => undefined);
    expect(success.status).toBe(200);
    expect(success.headers.get("Cache-Control")).toBe("no-store");
    expect(await success.json()).toEqual({ status: "ok" });

    const failure = await readyResponse(async () => { throw new Error("postgresql://secret@internal/db SQLSTATE 08006"); });
    expect(failure.status).toBe(503);
    const failureBody = await failure.text();
    expect(JSON.parse(failureBody)).toEqual({ status: "unavailable" });
    expect(failureBody).not.toMatch(/secret|internal|SQLSTATE|postgres/i);
  });

  it("exposes only validated release identity fields", async () => {
    const response = versionResponse({
      RELEASE_COMMIT_SHA: "591284b4b68afa5954442233aab3079f362384e1",
      BUILD_TIMESTAMP: "2026-10-03T12:00:00.000Z",
      APP_ENV: "staging",
      DATABASE_ADMIN_URL: "postgresql://secret@internal/db",
    });
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({
      commit: "591284b4b68afa5954442233aab3079f362384e1",
      buildTime: "2026-10-03T12:00:00.000Z",
      environment: "staging",
    });

    const unsafe = versionResponse({ RELEASE_COMMIT_SHA: "private token", BUILD_TIMESTAMP: "bad", APP_ENV: "preview-with-secret" });
    expect(await unsafe.json()).toEqual({ commit: "unknown", buildTime: "unknown", environment: "unknown" });
  });
});
