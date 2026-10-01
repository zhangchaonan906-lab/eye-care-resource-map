import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FacilityDetailContent } from "./facility-detail-content";
import { formatFacilityCategory, formatVerifiedDate, safeSourceUrl } from "./facility-presentation";

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
  attribution: [
    { name: "安全来源", url: "https://example.gov.cn/data", updatedAt: "2026-09-01" },
    { name: "不安全来源", url: "javascript:alert(1)", updatedAt: null },
  ],
  lastVerifiedAt: "2026-09-10T10:00:00.000Z",
  rawPayload: "must not appear",
};

describe("facility presentation", () => {
  it("only turns HTTPS attribution URLs into links", () => {
    expect(safeSourceUrl("https://example.gov.cn/path")).toBe("https://example.gov.cn/path");
    expect(safeSourceUrl("javascript:alert(1)")).toBeNull();
    expect(safeSourceUrl("http://example.gov.cn")).toBeNull();
  });

  it("formats categories and dates deterministically", () => {
    expect(formatFacilityCategory("eye_specialty_hospital")).toBe("眼科专科医院");
    expect(formatVerifiedDate("2026-09-10T10:00:00.000Z")).toBe("2026-09-10");
    expect(formatVerifiedDate(null)).toBe("公开来源信息暂缺");
  });

  it("renders only shareable public fields and links back to the map", () => {
    render(<FacilityDetailContent facility={facility} labels={new Map()} mapLink />);
    expect(screen.getByText("信息供查询，实际门诊与服务请以医院官方信息为准。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "在地图中查看" })).toHaveAttribute("href", `/resources/eye-hospitals?facility=${facility.id}`);
    expect(screen.getByRole("link", { name: "安全来源" })).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("不安全来源").tagName).toBe("SPAN");
    expect(screen.queryByText("医院级别")).not.toBeInTheDocument();
    expect(screen.queryByText("医院等级")).not.toBeInTheDocument();
    expect(screen.queryByText("must not appear")).not.toBeInTheDocument();
    expect(screen.queryByText(facility.id)).not.toBeInTheDocument();
  });
});
