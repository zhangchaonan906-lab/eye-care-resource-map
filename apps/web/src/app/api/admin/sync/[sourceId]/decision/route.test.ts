import { afterEach, describe, expect, it, vi } from "vitest";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE, createAdminSessionToken } from "@/lib/admin/auth";

const mocks = vi.hoisted(() => ({ decideSync: vi.fn() }));
vi.mock("@/lib/admin/repository", () => ({
  getAdminReviewRepository: () => ({ decideSync: mocks.decideSync }),
}));

import { POST } from "./route";

const actorId = "00000000-0000-4000-8000-000000001111";
const sourceId = "00000000-0000-4000-8000-000000002222";
const secret = "p12-admin-secret-that-is-longer-than-thirty-two-characters";
const csrf = "p12-csrf-token";

function request(action: string, options: { authenticated?: boolean; csrfValid?: boolean; key?: string } = {}) {
  const authenticated = options.authenticated ?? true;
  const token = createAdminSessionToken({ actorId, username: "reviewer", csrfToken: csrf }, secret);
  const cookie = authenticated
    ? `${ADMIN_SESSION_COOKIE}=${token}; ${ADMIN_CSRF_COOKIE}=${options.csrfValid === false ? "wrong" : csrf}`
    : "";
  return new Request(`https://app.example.test/api/admin/sync/${sourceId}/decision`, {
    method: "POST",
    headers: {
      Origin: "https://app.example.test", Cookie: cookie, "X-CSRF-Token": csrf,
      "Idempotency-Key": options.key ?? "00000000-0000-4000-8000-000000003333",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action, reason: "Controlled operator request" }),
  });
}

afterEach(() => { vi.unstubAllEnvs(); vi.clearAllMocks(); });

describe("admin sync decision endpoint", () => {
  it("requires an authenticated session, same-origin CSRF, and an idempotency key", async () => {
    vi.stubEnv("ADMIN_SESSION_SECRET", secret);
    expect((await POST(request("RUN_NOW", { authenticated: false }), { params: Promise.resolve({ sourceId }) })).status).toBe(401);
    expect((await POST(request("RUN_NOW", { csrfValid: false }), { params: Promise.resolve({ sourceId }) })).status).toBe(403);
    expect((await POST(request("RUN_NOW", { key: "bad" }), { params: Promise.resolve({ sourceId }) })).status).toBe(400);
    expect(mocks.decideSync).not.toHaveBeenCalled();
  });

  it("queues RUN_NOW with the session actor and returns 202", async () => {
    vi.stubEnv("ADMIN_SESSION_SECRET", secret);
    mocks.decideSync.mockResolvedValue({ taskId: "task-1", status: "queued" });
    const response = await POST(request("RUN_NOW"), { params: Promise.resolve({ sourceId }) });
    expect(response.status).toBe(202);
    expect(mocks.decideSync).toHaveBeenCalledWith(expect.objectContaining({ sourceId, actorId, action: "RUN_NOW" }));
  });

  it("returns MANUAL_FILE_REQUIRED without starting collection", async () => {
    vi.stubEnv("ADMIN_SESSION_SECRET", secret);
    mocks.decideSync.mockRejectedValue(Object.assign(new Error("MANUAL_FILE_REQUIRED"), { code: "23514" }));
    const response = await POST(request("RUN_NOW"), { params: Promise.resolve({ sourceId }) });
    expect(response.status).toBe(409);
    expect((await response.json()).error.code).toBe("MANUAL_FILE_REQUIRED");
  });
});
