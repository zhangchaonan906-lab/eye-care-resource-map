import { afterEach, describe, expect, it, vi } from "vitest";
import { checkRateLimit, type RateLimitPolicy } from "./distributed";

const policy: RateLimitPolicy = { name: "search", limit: 2, windowSeconds: 60 };

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("distributed rate limit", () => {
  it("uses a shared atomic Redis REST counter and hashes the client identifier", async () => {
    vi.stubEnv("APP_ENV", "production");
    vi.stubEnv("TRUST_PROXY_HEADERS", "true");
    vi.stubEnv("RATE_LIMIT_HASH_SECRET", "test-hash-secret");
    vi.stubEnv("UPSTASH_REDIS_REST_URL", "https://redis.example.test");
    vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "test-token");
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const command = JSON.parse(String(init?.body)) as string[];
      expect(command[0]).toBe("EVAL");
      expect(command[1]).toContain("INCR");
      expect(command[3]).not.toContain("203.0.113.7");
      return Response.json({ result: [1, 60] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await checkRateLimit(new Request("https://example.test/api/search", { headers: { "x-forwarded-for": "203.0.113.7" } }), policy);

    expect(result).toEqual({ allowed: true, limit: 2, remaining: 1, retryAfterSeconds: 0 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("uses an isolated local window in system-test mode despite local proxy headers", async () => {
    vi.stubEnv("APP_ENV", "staging");
    vi.stubEnv("P13_SYSTEM_TEST_MODE", "true");
    vi.stubEnv("TRUST_PROXY_HEADERS", "true");
    vi.stubEnv("RATE_LIMIT_HASH_SECRET", "system-test-hash-secret");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const systemPolicy = { name: "p13-system-only", limit: 2, windowSeconds: 60 };
    const request = new Request("https://example.test", { headers: { "x-forwarded-for": "localhost:3100" } });

    await expect(checkRateLimit(request, systemPolicy, 1_000)).resolves.toEqual({ allowed: true, limit: 2, remaining: 1, retryAfterSeconds: 0 });
    await expect(checkRateLimit(request, systemPolicy, 1_001)).resolves.toEqual({ allowed: true, limit: 2, remaining: 0, retryAfterSeconds: 0 });
    await expect(checkRateLimit(request, systemPolicy, 1_002)).resolves.toEqual({ allowed: false, limit: 2, remaining: 0, retryAfterSeconds: 60 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fails closed outside local/test when shared storage is missing", async () => {
    vi.stubEnv("APP_ENV", "staging");
    vi.stubEnv("TRUST_PROXY_HEADERS", "true");
    vi.stubEnv("RATE_LIMIT_HASH_SECRET", "test-hash-secret");
    vi.stubEnv("UPSTASH_REDIS_REST_URL", "");
    vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "");
    await expect(checkRateLimit(new Request("https://example.test", { headers: { "x-forwarded-for": "203.0.113.8" } }), policy)).rejects.toThrow("RATE_LIMIT_BACKEND_UNAVAILABLE");
  });

  it("returns retry metadata when the shared window is exhausted", async () => {
    vi.stubEnv("APP_ENV", "production");
    vi.stubEnv("TRUST_PROXY_HEADERS", "true");
    vi.stubEnv("RATE_LIMIT_HASH_SECRET", "test-hash-secret");
    vi.stubEnv("UPSTASH_REDIS_REST_URL", "https://redis.example.test");
    vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "test-token");
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ result: [3, 42] })));
    await expect(checkRateLimit(new Request("https://example.test", { headers: { "x-forwarded-for": "203.0.113.9" } }), policy)).resolves.toEqual({
      allowed: false, limit: 2, remaining: 0, retryAfterSeconds: 42,
    });
  });
});
