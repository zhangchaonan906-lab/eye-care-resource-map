import { describe, expect, it } from "vitest";
import { buildSecurityHeaders, shouldNoIndex } from "./security";

describe("release security headers", () => {
  it("sets baseline browser protections and a MapLibre-compatible report-only CSP", () => {
    const headers = new Map(buildSecurityHeaders("local", "").map(({ key, value }) => [key.toLowerCase(), value]));
    expect(headers.get("x-content-type-options")).toBe("nosniff");
    expect(headers.get("referrer-policy")).toBe("strict-origin-when-cross-origin");
    expect(headers.get("permissions-policy")).toContain("camera=()");
    expect(headers.get("permissions-policy")).toContain("microphone=()");
    expect(headers.get("permissions-policy")).toContain("geolocation=(self)");
    expect(headers.get("x-frame-options")).toBe("DENY");
    const csp = headers.get("content-security-policy-report-only") ?? "";
    expect(csp).toContain("worker-src 'self' blob:");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(headers.has("content-security-policy")).toBe(false);
  });

  it("adds HSTS only for a staging or production HTTPS site URL and omits preload", () => {
    expect(buildSecurityHeaders("staging", "http://localhost:3000").some(({ key }) => key === "Strict-Transport-Security")).toBe(false);
    expect(buildSecurityHeaders("staging", "").some(({ key }) => key === "Strict-Transport-Security")).toBe(false);
    const hsts = buildSecurityHeaders("staging", "https://staging.example.invalid")
      .find(({ key }) => key === "Strict-Transport-Security")?.value;
    expect(hsts).toBe("max-age=31536000");
    expect(hsts).not.toContain("preload");
  });

  it("prevents search indexing only in staging", () => {
    expect(shouldNoIndex("staging")).toBe(true);
    expect(shouldNoIndex("local")).toBe(false);
    expect(shouldNoIndex("production")).toBe(false);
  });
});
