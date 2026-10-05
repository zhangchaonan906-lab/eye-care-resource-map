import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  rateLimitResponse: vi.fn(async () => null),
  adminLogin: vi.fn(async () => Response.json({ ok: true })),
  adminLogout: vi.fn(() => Response.json({ ok: true })),
  adminSessionChallenge: vi.fn(() => Response.json({ data: { csrfToken: "challenge" } })),
  getAdminSession: vi.fn(() => Response.json({ data: { csrfToken: "session" } })),
}));

vi.mock("@/lib/rate-limit/distributed", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/rate-limit/distributed")>();
  return { ...original, rateLimitResponse: mocks.rateLimitResponse };
});
vi.mock("@/lib/admin/session-handlers", () => ({
  adminLogin: mocks.adminLogin,
  adminLogout: mocks.adminLogout,
  adminSessionChallenge: mocks.adminSessionChallenge,
  getAdminSession: mocks.getAdminSession,
}));

import { GET, POST } from "./route";
import { RATE_LIMITS } from "@/lib/rate-limit/distributed";

describe("admin session rate limits", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses a session-read budget for CSRF/session GET requests", async () => {
    await GET(new Request("https://example.test/api/admin/session"));
    expect(mocks.rateLimitResponse).toHaveBeenCalledWith(expect.any(Request), RATE_LIMITS.adminSession);
  });

  it("keeps login POST attempts on the stricter authentication budget", async () => {
    await POST(new Request("https://example.test/api/admin/session", { method: "POST" }));
    expect(mocks.rateLimitResponse).toHaveBeenCalledWith(expect.any(Request), RATE_LIMITS.adminLogin);
  });
});
