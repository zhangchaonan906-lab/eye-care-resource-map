import { beforeEach, describe, expect, it, vi } from "vitest";

const decideCorrection = vi.hoisted(() => vi.fn());
vi.mock("@/lib/admin/session-handlers", () => ({
  authenticatedSession: vi.fn(() => ({ actorId: "00000000-0000-4000-8000-000000000002" })),
  mutationIsAllowed: vi.fn(() => true),
}));
vi.mock("@/lib/admin/repository", () => ({ getAdminReviewRepository: () => ({ decideCorrection }) }));
import { POST } from "./route";

const reportId = "00000000-0000-4000-8000-000000000001";
const requestId = "00000000-0000-4000-8000-000000000003";

describe("correction review decision", () => {
  beforeEach(() => decideCorrection.mockReset().mockResolvedValue({ reportId, status: "reviewing" }));
  it("uses a validated idempotency key and bounded decision input", async () => {
    const response = await POST(new Request(`https://example.test/api/admin/corrections/${reportId}/decision`, {
      method: "POST", headers: { "content-type": "application/json", "idempotency-key": requestId },
      body: JSON.stringify({ action: "START_REVIEW", reason: "人工审核开始" }),
    }), { params: Promise.resolve({ id: reportId }) });
    expect(response.status).toBe(200);
    expect(decideCorrection).toHaveBeenCalledWith({ reportId, actorId: "00000000-0000-4000-8000-000000000002", requestId, action: "START_REVIEW", reason: "人工审核开始" });
  });
  it("rejects invalid actions and short reasons before database access", async () => {
    const response = await POST(new Request(`https://example.test/api/admin/corrections/${reportId}/decision`, {
      method: "POST", headers: { "content-type": "application/json", "idempotency-key": requestId },
      body: JSON.stringify({ action: "PUBLISH", reason: "bad" }),
    }), { params: Promise.resolve({ id: reportId }) });
    expect(response.status).toBe(400);
    expect(decideCorrection).not.toHaveBeenCalled();
  });
});
