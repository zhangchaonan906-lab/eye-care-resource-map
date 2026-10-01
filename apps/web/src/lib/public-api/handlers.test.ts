import { describe, expect, it, vi } from "vitest";
import { categoriesHandler, detailHandler, facilitiesHandler, searchHandler } from "./handlers";
import type { PublicFacility, PublicFacilityRepository } from "./types";

const facility: PublicFacility = {
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
  attribution: [{ name: "官方来源", url: "https://example.org/dataset", updatedAt: null }],
  lastVerifiedAt: "2026-09-01T00:00:00.000Z",
};

function repository(overrides: Partial<PublicFacilityRepository> = {}): PublicFacilityRepository {
  return {
    list: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
    getById: vi.fn().mockResolvedValue(null),
    search: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
    ...overrides,
  };
}

describe("GET /api/facilities", () => {
  it("requires valid bbox and rejects malformed or out-of-range bounds", async () => {
    const repo = repository();
    for (const query of ["", "bbox=1,2,3", "bbox=1,2,3,no", "bbox=181,0,182,1", "bbox=2,0,1,1", "bbox=0,91,1,92"]) {
      const response = await facilitiesHandler(new Request(`https://local.test/api/facilities?${query}`), repo);
      expect(response.status).toBe(400);
    }
    expect(repo.list).not.toHaveBeenCalled();
  });

  it("bounds limits, validates category/region/cursor, and returns empty results safely", async () => {
    const repo = repository();
    for (const query of [
      "bbox=1,2,3,4&limit=0",
      "bbox=1,2,3,4&limit=501",
      "bbox=1,2,3,4&category=not-a-category",
      "bbox=1,2,3,4&region=abc",
      "bbox=1,2,3,4&cursor=not-base64",
    ]) {
      expect((await facilitiesHandler(new Request(`https://local.test/api/facilities?${query}`), repo)).status).toBe(400);
    }
    const response = await facilitiesHandler(new Request("https://local.test/api/facilities?bbox=116,39,117,40"), repo);
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ data: [], meta: { count: 0, nextCursor: null }, error: null });
  });

  it("returns allowlisted data and a stable envelope", async () => {
    const repo = repository({ list: vi.fn().mockResolvedValue({ items: [facility], nextCursor: "next" }) });
    const response = await facilitiesHandler(new Request("https://local.test/api/facilities?bbox=116,39,117,40&limit=3"), repo);
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toMatchObject({ data: [facility], meta: { count: 1, nextCursor: "next" }, error: null });
    expect(JSON.stringify(body)).not.toMatch(/法人|负责人|raw_payload|source_record/i);
  });

  it("maps internal errors to generic 500 without leaking details", async () => {
    const repo = repository({ list: vi.fn().mockRejectedValue(new Error("select * from private_table")) });
    const response = await facilitiesHandler(new Request("https://local.test/api/facilities?bbox=116,39,117,40"), repo);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body).toEqual({ data: null, meta: null, error: { code: "INTERNAL_ERROR", message: "服务暂不可用" } });
    expect(JSON.stringify(body)).not.toContain("private_table");
  });
});

describe("facility detail", () => {
  it("validates UUID and returns 404 for absent facilities", async () => {
    const repo = repository();
    expect((await detailHandler(new Request("https://local.test/api/facilities/nope"), "nope", repo)).status).toBe(400);
    const response = await detailHandler(new Request("https://local.test/api/facilities/00000000-0000-4000-8000-000000000099"), "00000000-0000-4000-8000-000000000099", repo);
    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ data: null, meta: null, error: { code: "NOT_FOUND", message: "未找到该医疗机构" } });
  });

  it("returns only published facility shape", async () => {
    const repo = repository({ getById: vi.fn().mockResolvedValue(facility) });
    const response = await detailHandler(new Request("https://local.test/api/facilities/00000000-0000-4000-8000-000000000001"), facility.id, repo);
    expect(response.status).toBe(200);
    expect((await response.json()).data).toEqual(facility);
  });
});

describe("search and categories", () => {
  it("requires q, validates parameters, supports exact and partial search", async () => {
    const repo = repository();
    for (const query of ["", "q=x&limit=21", "q=x&category=bad", "q=x&region=abc"]) {
      expect((await searchHandler(new Request(`https://local.test/api/search?${query}`), repo)).status).toBe(400);
    }
    const exact = await searchHandler(new Request("https://local.test/api/search?q=%E6%B5%8B%E8%AF%95%E7%9C%BC%E7%A7%91%E5%8C%BB%E9%99%A2&match=exact"), repo);
    const partial = await searchHandler(new Request("https://local.test/api/search?q=%E7%9C%BC%E7%A7%91&match=prefix"), repo);
    expect(exact.status).toBe(200);
    expect(partial.status).toBe(200);
    expect(repo.search).toHaveBeenCalledTimes(2);
    expect(vi.mocked(repo.search).mock.calls.map(([input]) => input.match)).toEqual(["exact", "prefix"]);
  });

  it("returns all five supported categories", async () => {
    const response = await categoriesHandler();
    expect(response.status).toBe(200);
    expect((await response.json()).data.map((item: { id: string }) => item.id)).toEqual([
      "eye_specialty_hospital",
      "general_hospital_ophthalmology",
      "ophthalmology_center",
      "eye_clinic",
      "unknown",
    ]);
  });
});
