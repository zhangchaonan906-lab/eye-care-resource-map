import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mocks = vi.hoisted(() => ({
  getById: vi.fn(),
  notFound: vi.fn(() => { throw new Error("NOT_FOUND"); }),
}));

vi.mock("next/navigation", () => ({ notFound: mocks.notFound }));
vi.mock("../../../lib/public-api/repository", () => ({
  getPublicFacilityRepository: () => ({ getById: mocks.getById }),
}));

import HospitalDetailPage, { generateMetadata } from "./page";

const facility = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "公开眼科医院",
  category: "eye_specialty_hospital" as const,
  address: "示例路 1 号",
  region: { adcode: "110101", name: "北京市东城区" },
  hospitalLevel: null,
  hospitalGrade: null,
  longitude: 116.4,
  latitude: 39.9,
  ophthalmology: { status: "verified" as const, evidenceCount: 2 },
  attribution: [],
  lastVerifiedAt: "2026-09-10T10:00:00.000Z",
};

describe("hospital detail route", () => {
  beforeEach(() => {
    mocks.getById.mockReset();
    mocks.notFound.mockClear();
  });

  it("renders public published fields and a map deep link", async () => {
    mocks.getById.mockResolvedValue(facility);
    render(await HospitalDetailPage({ params: Promise.resolve({ id: facility.id }) }));
    expect(screen.getByRole("heading", { name: facility.name })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "在地图中查看" })).toHaveAttribute("href", `/resources/eye-hospitals?facility=${facility.id}`);
    expect(screen.getByText("公开来源信息暂缺")).toBeInTheDocument();
    expect(screen.getByText("信息供查询，实际门诊与服务请以医院官方信息为准。")).toBeInTheDocument();
    expect(screen.queryByText(facility.id)).not.toBeInTheDocument();
  });

  it.each([
    ["invalid UUID", "not-an-id"],
    ["unpublished facility", "00000000-0000-4000-8000-000000000002"],
  ])("uses the same 404 for %s", async (_label, id) => {
    mocks.getById.mockResolvedValue(null);
    await expect(HospitalDetailPage({ params: Promise.resolve({ id }) })).rejects.toThrow("NOT_FOUND");
    expect(mocks.notFound).toHaveBeenCalledOnce();
  });

  it("generates metadata from available public fields and omits detail metadata for missing facilities", async () => {
    mocks.getById.mockResolvedValue(facility);
    await expect(generateMetadata({ params: Promise.resolve({ id: facility.id }) })).resolves.toEqual({
      title: "公开眼科医院｜全国眼科医疗资源地图",
      description: "北京市东城区 · 示例路 1 号 · 已核验眼科医疗资源",
    });
    mocks.getById.mockResolvedValue(null);
    await expect(generateMetadata({ params: Promise.resolve({ id: facility.id }) })).resolves.toEqual({});
  });
});
