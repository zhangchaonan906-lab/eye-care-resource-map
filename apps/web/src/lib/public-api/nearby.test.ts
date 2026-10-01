import { describe, expect, it, vi } from "vitest";
import { nearbyHandler } from "./handlers";
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

const base = "https://local.test/api/nearby?lat=39.9&lng=116.4";

describe("GET /api/nearby", () => {
  it("uses WGS84 input, default radius and limit, and returns only public fields plus distance", async () => {
    const repo = repository({ nearby: vi.fn().mockResolvedValue({ items: [item], truncated: false }) });
    const response = await nearbyHandler(new Request(base), repo);
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(repo.nearby).toHaveBeenCalledWith({ latitude: 39.9, longitude: 116.4, radiusMeters: 10_000, limit: 50 });
    expect(await response.json()).toEqual({
      data: [item],
      meta: { count: 1, radiusMeters: 10_000, truncated: false },
      error: null,
    });
  });

  it("rejects missing, non-finite, out-of-range coordinates and invalid radius, limit, or category before repository access", async () => {
    const repo = repository();
    const invalidQueries = [
      "lng=116.4",
      "lat=39.9",
      "lat=NaN&lng=116.4",
      "lat=Infinity&lng=116.4",
      "lat=90.01&lng=116.4",
      "lat=-90.01&lng=116.4",
      "lat=39.9&lng=180.01",
      "lat=39.9&lng=-180.01",
      "lat=39.9&lng=116.4&radius=499",
      "lat=39.9&lng=116.4&radius=50001",
      "lat=39.9&lng=116.4&limit=101",
      "lat=39.9&lng=116.4&limit=NaN",
      "lat=39.9&lng=116.4&category=invalid",
    ];
    for (const query of invalidQueries) {
      const response = await nearbyHandler(new Request(`https://local.test/api/nearby?${query}`), repo);
      expect(response.status, query).toBe(400);
      expect(response.headers.get("Cache-Control")).toBe("no-store");
      expect((await response.json()).error.code).toBe("INVALID_ARGUMENT");
    }
    expect(repo.nearby).not.toHaveBeenCalled();
  });

  it("passes optional radius, category, and bounded limit", async () => {
    const repo = repository();
    const response = await nearbyHandler(new Request(`${base}&radius=50000&limit=100&category=eye_clinic`), repo);
    expect(response.status).toBe(200);
    expect(repo.nearby).toHaveBeenCalledWith({
      latitude: 39.9,
      longitude: 116.4,
      radiusMeters: 50_000,
      category: "eye_clinic",
      limit: 100,
    });
  });

  it("returns zero-result and truncation metadata without echoing user coordinates", async () => {
    const empty = await nearbyHandler(new Request(base), repository());
    expect(await empty.json()).toMatchObject({ data: [], meta: { count: 0, radiusMeters: 10_000, truncated: false } });

    const truncated = await nearbyHandler(
      new Request("https://local.test/api/nearby?lat=39.91&lng=116.41&limit=1"),
      repository({ nearby: vi.fn().mockResolvedValue({ items: [item], truncated: true }) }),
    );
    const body = await truncated.json();
    expect(body.meta.truncated).toBe(true);
    expect(JSON.stringify(body)).not.toContain('"latitude":39.91');
    expect(JSON.stringify(body)).not.toContain('"longitude":116.41');
  });

  it("maps repository errors to a generic 500 response", async () => {
    const response = await nearbyHandler(
      new Request(base),
      repository({ nearby: vi.fn().mockRejectedValue(new Error("private SQL and 39.9,116.4")) }),
    );
    expect(response.status).toBe(500);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({ data: null, meta: null, error: { code: "INTERNAL_ERROR", message: "服务暂不可用" } });
  });
});
