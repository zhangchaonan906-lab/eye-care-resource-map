import { describe, expect, it, vi } from "vitest";
import { nearbyPostHandler, nearbyMethodNotAllowed } from "./handlers";
import type { NearbyFacility, PublicFacilityRepository } from "./types";

const item: NearbyFacility = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "测试眼科医院",
  category: "eye_specialty_hospital",
  address: "测试路1号",
  region: { adcode: "110000", name: "北京市" },
  hospitalLevel: null,
  hospitalGrade: null,
  longitude: 116.4,
  latitude: 39.9,
  ophthalmology: { status: "verified", evidenceCount: 1 },
  attribution: [],
  lastVerifiedAt: "2026-09-01T00:00:00.000Z",
  distanceMeters: 620,
};

function repository(overrides: Partial<PublicFacilityRepository> = {}): PublicFacilityRepository {
  return {
    list: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
    getById: vi.fn().mockResolvedValue(null),
    search: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
    nearby: vi.fn().mockResolvedValue({ items: [], truncated: false }),
    countPublished: vi.fn().mockResolvedValue(0),
    ...overrides,
  };
}

function request(body: unknown, url = "https://local.test/api/nearby") {
  return new Request(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

describe("POST /api/nearby", () => {
  it("uses WGS84 body coordinates, default radius and limit, and returns only public fields plus distance", async () => {
    const repo = repository({ nearby: vi.fn().mockResolvedValue({ items: [item], truncated: false }) });
    const response = await nearbyPostHandler(request({ lat: 39.9, lng: 116.4 }), repo);
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(repo.nearby).toHaveBeenCalledWith({ latitude: 39.9, longitude: 116.4, radiusMeters: 10_000, limit: 50 });
    expect(await response.json()).toEqual({
      data: [item],
      meta: { count: 1, radiusMeters: 10_000, truncated: false },
      error: null,
    });
  });

  it("keeps the exact coordinates out of the request URL and response", async () => {
    const input = request({ lat: 39.123456, lng: 116.654321 }, "https://local.test/api/nearby");
    expect(new URL(input.url).search).toBe("");
    const response = await nearbyPostHandler(input, repository());
    const body = await response.text();
    expect(response.url).toBe("");
    expect(body).not.toContain("39.123456");
    expect(body).not.toContain("116.654321");
  });

  it("does not write nearby request coordinates to application logs", async () => {
    const methods = ["log", "info", "warn", "error", "debug"] as const;
    const spies = methods.map((method) => vi.spyOn(console, method));
    try {
      await nearbyPostHandler(request({ lat: 39.123456, lng: 116.654321 }), repository());
      const logOutput = spies.flatMap((spy) => spy.mock.calls.flat()).join(" ");
      expect(logOutput).not.toContain("39.123456");
      expect(logOutput).not.toContain("116.654321");
    } finally {
      spies.forEach((spy) => spy.mockRestore());
    }
  });

  it("rejects malformed, missing, out-of-range coordinates and invalid radius, limit, or category", async () => {
    const repo = repository();
    const bodies: unknown[] = [
      {}, { lat: 39.9 }, { lng: 116.4 }, { lat: "NaN", lng: 116.4 },
      { lat: 90.01, lng: 116.4 }, { lat: -90.01, lng: 116.4 },
      { lat: 39.9, lng: 180.01 }, { lat: 39.9, lng: -180.01 },
      { lat: 39.9, lng: 116.4, radius: 499 }, { lat: 39.9, lng: 116.4, radius: 50_001 },
      { lat: 39.9, lng: 116.4, limit: 101 }, { lat: 39.9, lng: 116.4, limit: 1.5 },
      { lat: 39.9, lng: 116.4, category: "invalid" }, null, [],
    ];
    for (const body of bodies) {
      const response = await nearbyPostHandler(request(body), repo);
      expect(response.status, JSON.stringify(body)).toBe(400);
      expect(response.headers.get("Cache-Control")).toBe("no-store");
      expect((await response.json()).error.code).toBe("INVALID_ARGUMENT");
    }
    expect(repo.nearby).not.toHaveBeenCalled();
  });

  it("returns 400 for malformed or oversized JSON without echoing the request", async () => {
    const repo = repository();
    const malformed = await nearbyPostHandler(new Request("https://local.test/api/nearby", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{",
    }), repo);
    expect(malformed.status).toBe(400);
    const marker = "private-marker";
    const body = JSON.stringify({ lat: 39.9, lng: 116.4, extra: marker.repeat(400) });
    {
      const response = await nearbyPostHandler(new Request("https://local.test/api/nearby", {
        method: "POST", headers: { "Content-Type": "application/json" }, body,
      }), repo);
      expect(response.status).toBe(400);
      expect(await response.text()).not.toContain(marker);
    }
    expect(repo.nearby).not.toHaveBeenCalled();
  });

  it("passes optional radius, category, and bounded limit", async () => {
    const repo = repository();
    const response = await nearbyPostHandler(request({ lat: 39.9, lng: 116.4, radius: 50_000, limit: 100, category: "eye_clinic" }), repo);
    expect(response.status).toBe(200);
    expect(repo.nearby).toHaveBeenCalledWith({ latitude: 39.9, longitude: 116.4, radiusMeters: 50_000, category: "eye_clinic", limit: 100 });
  });

  it("returns zero-result and truncation metadata without coordinates", async () => {
    const empty = await nearbyPostHandler(request({ lat: 39.9, lng: 116.4 }), repository());
    expect(await empty.json()).toMatchObject({ data: [], meta: { count: 0, radiusMeters: 10_000, truncated: false } });
    const truncated = await nearbyPostHandler(
      request({ lat: 39.91, lng: 116.41, limit: 1 }),
      repository({ nearby: vi.fn().mockResolvedValue({ items: [item], truncated: true }) }),
    );
    const body = JSON.stringify(await truncated.json());
    expect(body).not.toContain("39.91");
    expect(body).not.toContain("116.41");
  });

  it("maps repository errors to a generic 500 response", async () => {
    const response = await nearbyPostHandler(
      request({ lat: 39.9, lng: 116.4 }),
      repository({ nearby: vi.fn().mockRejectedValue(new Error("private SQL and 39.9,116.4")) }),
    );
    expect(response.status).toBe(500);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({ data: null, meta: null, error: { code: "INTERNAL_ERROR", message: "服务暂不可用" } });
  });

  it("disables the old coordinate-in-query GET contract", async () => {
    const response = nearbyMethodNotAllowed();
    expect(response.status).toBe(405);
    expect(response.headers.get("Allow")).toBe("POST");
    expect(response.headers.get("Cache-Control")).toBe("no-store");
  });
});
