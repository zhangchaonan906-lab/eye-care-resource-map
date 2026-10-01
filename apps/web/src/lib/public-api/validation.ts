import { FACILITY_CATEGORIES, type FacilityCategory } from "./types";

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

export type CursorValue = { kind: "id"; id: string } | { kind: "search"; name: string; id: string };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function parseUuid(value: string): string {
  if (!UUID.test(value)) throw new ValidationError("id 格式无效");
  return value.toLowerCase();
}

export function parseCategory(value: string | null): FacilityCategory | undefined {
  if (value === null) return undefined;
  if (!(FACILITY_CATEGORIES as readonly string[]).includes(value)) throw new ValidationError("category 无效");
  return value as FacilityCategory;
}

export function parseRegion(value: string | null): string | undefined {
  if (value === null) return undefined;
  if (!/^(?:\d{2}|\d{4}|\d{6})$/.test(value)) throw new ValidationError("region 必须是 2、4 或 6 位行政区划代码前缀");
  return value;
}

function parseLimit(value: string | null, fallback: number, max: number): number {
  if (value === null) return fallback;
  if (!/^\d+$/.test(value)) throw new ValidationError("limit 必须是正整数");
  const parsed = Number(value);
  if (parsed < 1 || parsed > max) throw new ValidationError(`limit 必须在 1 到 ${max} 之间`);
  return parsed;
}

export function decodeCursor(token: string | null, expected: CursorValue["kind"]): CursorValue | undefined {
  if (token === null) return undefined;
  if (token.length > 512 || !/^[A-Za-z0-9_-]+$/.test(token)) throw new ValidationError("cursor 无效");
  try {
    const raw = Buffer.from(token, "base64url").toString("utf8");
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object") throw new Error("shape");
    const record = value as Record<string, unknown>;
    if (record.kind !== expected || typeof record.id !== "string" || !UUID.test(record.id)) throw new Error("shape");
    if (expected === "id") return { kind: "id", id: record.id.toLowerCase() };
    if (typeof record.name !== "string" || record.name.length > 512) throw new Error("shape");
    return { kind: "search", name: record.name, id: record.id.toLowerCase() };
  } catch {
    throw new ValidationError("cursor 无效");
  }
}

export function encodeCursor(value: CursorValue): string {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

export function parseFacilityQuery(url: URL) {
  const raw = url.searchParams.get("bbox");
  if (!raw) throw new ValidationError("bbox 是必填参数");
  const parts = raw.split(",");
  const decimal = /^-?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;
  if (parts.length !== 4 || parts.some((part) => !decimal.test(part.trim()) || !Number.isFinite(Number(part)))) {
    throw new ValidationError("bbox 必须为 west,south,east,north 四个数字");
  }
  const bbox = parts.map(Number) as [number, number, number, number];
  const [west, south, east, north] = bbox;
  if (west < -180 || east > 180 || west >= east || south < -90 || north > 90 || south >= north) {
    throw new ValidationError("bbox 超出经纬度范围或边界顺序无效");
  }
  const limit = parseLimit(url.searchParams.get("limit"), 100, 500);
  const cursor = decodeCursor(url.searchParams.get("cursor"), "id");
  return {
    bbox,
    category: parseCategory(url.searchParams.get("category")),
    region: parseRegion(url.searchParams.get("region")),
    limit,
    cursor: cursor?.id,
  };
}

export function normalizeSearchTerm(value: string): string {
  return value.normalize("NFKC").trim().replace(/\s+/g, " ");
}

export function parseSearchQuery(url: URL) {
  const q = normalizeSearchTerm(url.searchParams.get("q") ?? "");
  if (!q || q.length > 100) throw new ValidationError("q 必须为 1 到 100 个字符");
  const matchValue = url.searchParams.get("match") ?? "prefix";
  if (matchValue !== "exact" && matchValue !== "prefix") throw new ValidationError("match 只支持 exact 或 prefix");
  const limit = parseLimit(url.searchParams.get("limit"), 20, 20);
  const cursor = decodeCursor(url.searchParams.get("cursor"), "search");
  return {
    q,
    match: matchValue,
    category: parseCategory(url.searchParams.get("category")),
    region: parseRegion(url.searchParams.get("region")),
    limit,
    cursor: cursor?.kind === "search" ? { name: cursor.name, id: cursor.id } : undefined,
  } as const;
}
