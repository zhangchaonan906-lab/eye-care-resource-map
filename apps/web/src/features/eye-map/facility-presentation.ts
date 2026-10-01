import { FACILITY_CATEGORY_LABELS, type FacilityCategory } from "../../lib/public-api/types";

export function formatFacilityCategory(category: FacilityCategory, labels: Map<string, string> = new Map()): string {
  return labels.get(category) ?? FACILITY_CATEGORY_LABELS[category] ?? "医疗机构";
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
