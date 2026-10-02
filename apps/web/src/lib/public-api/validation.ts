import {
  FACILITY_CATEGORIES,
  MAX_MAP_ZOOM,
  MIN_FACILITY_DETAIL_ZOOM,
  type FacilityCategory,
} from "./types";

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

export class ViewportTooLargeError extends Error {
  constructor() {
    super("请放大地图后查看医疗机构");
    this.name = "ViewportTooLargeError";
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

export function normalizeSearchTerm(value: string): string {
  return value.normalize("NFKC").trim().replace(/\s+/g, " ");
}

type ViewportTier = { maxZoom: number; maxLngSpan: number; maxLatSpan: number };
const VIEWPORT_TIERS: readonly ViewportTier[] = [
  { maxZoom: 9, maxLngSpan: 6, maxLatSpan: 4 },
  { maxZoom: 12, maxLngSpan: 3, maxLatSpan: 2 },
  { maxZoom: 15, maxLngSpan: 1.5, maxLatSpan: 1 },
  { maxZoom: 18, maxLngSpan: 0.75, maxLatSpan: 0.5 },
  { maxZoom: MAX_MAP_ZOOM, maxLngSpan: 0.35, maxLatSpan: 0.25 },
];

export function validateViewport(
  bbox: [number, number, number, number],
  zoom: number,
): void {
  if (!Number.isFinite(zoom) || zoom < 0 || zoom > MAX_MAP_ZOOM) {
    throw new ValidationError(`zoom 必须在 0 到 ${MAX_MAP_ZOOM} 之间`);
  }
  if (zoom < MIN_FACILITY_DETAIL_ZOOM) throw new ViewportTooLargeError();

  const tier = VIEWPORT_TIERS.find(({ maxZoom }) => zoom <= maxZoom);
  if (!tier) throw new ValidationError("zoom 超出允许范围");
  const longitudeSpan = bbox[2] - bbox[0];
  const latitudeSpan = bbox[3] - bbox[1];
  if (longitudeSpan > tier.maxLngSpan || latitudeSpan > tier.maxLatSpan) {
    throw new ViewportTooLargeError();
  }
}

export function parseSearchQuery(url: URL) {
  const q = normalizeSearchTerm(url.searchParams.get("q") ?? "");
  if (!q || q.length > 100 || /[\u0000-\u001f\u007f-\u009f]/.test(q)) {
    throw new ValidationError("q 必须为 1 到 100 个不含控制字符的字符");
  }
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
  const rawZoom = url.searchParams.get("zoom");
  if (rawZoom === null || !decimal.test(rawZoom.trim())) throw new ValidationError("zoom 是必填数字");
  const zoom = Number(rawZoom);
  validateViewport(bbox, zoom);
  const limit = parseLimit(url.searchParams.get("limit"), 100, 500);
  const cursor = decodeCursor(url.searchParams.get("cursor"), "id");
  return {
    bbox,
    zoom,
    category: parseCategory(url.searchParams.get("category")),
    region: parseRegion(url.searchParams.get("region")),
    limit,
    cursor: cursor?.id,
  };
}

const DECIMAL = /^-?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;

function parseFiniteCoordinate(value: string | null, name: "lat" | "lng", min: number, max: number): number {
  if (value === null || !DECIMAL.test(value.trim())) throw new ValidationError(`${name} 必须是有效经纬度`);
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) throw new ValidationError(`${name} 超出有效范围`);
  return parsed;
}

export function parseNearbyQuery(url: URL) {
  const latitude = parseFiniteCoordinate(url.searchParams.get("lat"), "lat", -90, 90);
  const longitude = parseFiniteCoordinate(url.searchParams.get("lng"), "lng", -180, 180);
  const rawRadius = url.searchParams.get("radius");
  const radiusMeters = rawRadius === null ? 10_000 : Number(rawRadius);
  if (rawRadius !== null && (!DECIMAL.test(rawRadius.trim()) || !Number.isFinite(radiusMeters) || radiusMeters < 500 || radiusMeters > 50_000)) {
    throw new ValidationError("radius 必须在 500 到 50000 米之间");
  }
  const limit = parseLimit(url.searchParams.get("limit"), 50, 100);
  return { latitude, longitude, radiusMeters, category: parseCategory(url.searchParams.get("category")), limit };
}
