import { beforeEach, describe, expect, it, vi } from "vitest";

const submit = vi.hoisted(() => vi.fn());
vi.mock("@/lib/corrections/repository", () => ({ getCorrectionRepository: () => ({ submit }) }));
vi.mock("@/lib/rate-limit/distributed", () => ({ rateLimitResponse: vi.fn(async () => null), RATE_LIMITS: { correction: {} } }));
import { POST } from "./route";

function request(body: string, headers: Record<string, string> = { origin: "https://example.test", host: "example.test" }) {
  return new Request("https://example.test/api/corrections", { method: "POST", headers: { "content-type": "application/json", ...headers }, body });
}

describe("POST /api/corrections", () => {
  beforeEach(() => { submit.mockReset().mockResolvedValue("00000000-0000-4000-8000-000000000001"); });
  it("queues bounded same-origin reports and returns pending without facility mutation operations", async () => {
    const response = await POST(request(JSON.stringify({ type: "closed", description: "已停止营业，请核实。" })));
    expect(response.status).toBe(202);
    expect(await response.json()).toMatchObject({ data: { status: "pending" } });
    expect(submit).toHaveBeenCalledWith({ type: "closed", description: "已停止营业，请核实。" });
  });
  it("rejects cross-origin and malformed reports before database access", async () => {
    expect((await POST(request("{}", { origin: "https://attacker.test", host: "example.test" }))).status).toBe(403);
    expect((await POST(request(JSON.stringify({ type: "closed", description: "short" })))).status).toBe(400);
    expect(submit).not.toHaveBeenCalled();
  });
  it("rejects bodies over the byte budget", async () => {
    const response = await POST(request(JSON.stringify({ type: "closed", description: "x".repeat(5000) })));
    expect(response.status).toBe(413);
    expect(submit).not.toHaveBeenCalled();
  });
});
