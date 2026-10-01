import type { FacilityCategory } from "../../lib/public-api/types";

const CATEGORY_LABELS: Record<FacilityCategory, string> = {
  eye_specialty_hospital: "眼科专科医院",
  general_hospital_ophthalmology: "设有眼科的综合医院",
  ophthalmology_center: "眼科中心",
  eye_clinic: "眼科诊所",
  unknown: "待核验",
};

export function formatFacilityCategory(category: FacilityCategory, labels: Map<string, string> = new Map()): string {
  return labels.get(category) ?? CATEGORY_LABELS[category] ?? "医疗机构";
}

export function safeSourceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function formatVerifiedDate(value: string | null | undefined): string {
  if (!value) return "公开来源信息暂缺";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "公开来源信息暂缺";
  return date.toISOString().slice(0, 10);
}
