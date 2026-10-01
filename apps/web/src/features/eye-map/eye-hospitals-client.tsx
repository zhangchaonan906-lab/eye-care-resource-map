"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PublicFacility } from "../../lib/public-api/types";
import type { FacilityMapController, Viewport } from "../../lib/map/map-adapter";
import { MIN_FACILITY_DETAIL_ZOOM } from "../../lib/public-api/types";
import { FacilityDetailPanel } from "./facility-detail-panel";
import { FacilityList } from "./facility-list";
import { LocationControl } from "./location-control";
import { MapCanvas } from "./map-canvas";
import { SearchAndFilters, type CategoryOption } from "./search-and-filters";

type ViewportState = Viewport | null;
type LoadState = "idle" | "loading" | "ready" | "empty" | "zoom" | "too-large" | "incomplete" | "error" | "region-invalid";
const CLIENT_FACILITY_CAP = 1200;
const API_PAGE_SIZE = 500;

function isRegionCodeValid(value: string): boolean {
  return !value.trim() || /^(?:\d{2}|\d{4}|\d{6})$/.test(value.trim());
}

async function readJson(response: Response): Promise<Record<string, unknown>> {
  try { return await response.json() as Record<string, unknown>; }
  catch { return {}; }
}

function messageFrom(payload: Record<string, unknown>, fallback: string): string {
  const error = payload.error;
  if (error && typeof error === "object" && typeof (error as { message?: unknown }).message === "string") return (error as { message: string }).message;
  return fallback;
}

export function EyeHospitalsClient() {
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [publishedFacilityCount, setPublishedFacilityCount] = useState<number | null>(null);
  const [category, setCategory] = useState("");
  const [region, setRegion] = useState("");
  const [viewport, setViewport] = useState<ViewportState>(null);
  const [facilities, setFacilities] = useState<PublicFacility[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("zoom");
  const [apiError, setApiError] = useState<string | null>(null);
  const [basemapError, setBasemapError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PublicFacility | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<PublicFacility[]>([]);
  const [searchState, setSearchState] = useState<"idle" | "loading" | "ready" | "empty" | "error" | "invalid">("idle");
  const mapControllerRef = useRef<FacilityMapController | null>(null);

  const labels = useMemo(() => new Map(categories.map((item) => [item.id, item.label])), [categories]);
  const selectedForMap = useCallback((id: string) => {
    setSelectedId(id);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
  }, []);
  const clearSelection = useCallback(() => {
    setSelectedId(null);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(false);
  }, []);
  const changeViewport = useCallback((next: Viewport) => {
    if (next.zoom < MIN_FACILITY_DETAIL_ZOOM) {
      setFacilities([]);
      setLoadState("zoom");
      setApiError(null);
    }
    setViewport(next);
  }, []);
  const receiveController = useCallback((controller: FacilityMapController | null) => { mapControllerRef.current = controller; }, []);
  const mapError = useCallback(() => setBasemapError(true), []);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/meta/categories", { signal: controller.signal }).then(readJson).then((payload) => {
      if (Array.isArray(payload.data)) {
        const parsed = payload.data.filter((value): value is { id: string; label: string } => Boolean(value && typeof value === "object" && typeof (value as { id?: unknown }).id === "string" && typeof (value as { label?: unknown }).label === "string"));
        setCategories(parsed);
      }
      const meta = payload.meta && typeof payload.meta === "object" ? payload.meta as { publishedFacilityCount?: unknown } : {};
      if (typeof meta.publishedFacilityCount === "number" && Number.isFinite(meta.publishedFacilityCount)) setPublishedFacilityCount(meta.publishedFacilityCount);
    }).catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setApiError("机构类型暂时无法加载"); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!viewport || !isRegionCodeValid(region)) return;
    if (viewport.zoom < MIN_FACILITY_DETAIL_ZOOM) return;
    const controller = new AbortController();
    let current = true;
    const timer = window.setTimeout(async () => {
      if (current) {
        setLoadState("loading");
        setApiError(null);
      }
      try {
        const collected: PublicFacility[] = [];
        let cursor: string | null = null;
        do {
          const remaining = Math.max(1, CLIENT_FACILITY_CAP - collected.length);
          const params = new URLSearchParams({ bbox: viewport.bbox.join(","), zoom: String(viewport.zoom), limit: String(Math.min(API_PAGE_SIZE, remaining)) });
          if (category) params.set("category", category);
          if (region.trim()) params.set("region", region.trim());
          if (cursor) params.set("cursor", cursor);
          const response = await fetch(`/api/facilities?${params.toString()}`, { signal: controller.signal });
          const payload = await readJson(response);
          if (!response.ok) {
            const error = payload.error as { code?: string } | undefined;
            if (response.status === 400 && error?.code === "VIEWPORT_TOO_LARGE") {
              if (current) { setFacilities([]); setLoadState("too-large"); }
              return;
            }
            throw new Error(messageFrom(payload, "机构数据加载失败，请稍后重试"));
          }
          const rows = Array.isArray(payload.data) ? payload.data as PublicFacility[] : [];
          collected.push(...rows);
          const meta = payload.meta && typeof payload.meta === "object" ? payload.meta as { nextCursor?: unknown } : {};
          cursor = typeof meta.nextCursor === "string" && meta.nextCursor ? meta.nextCursor : null;
          if (collected.length >= CLIENT_FACILITY_CAP && cursor) {
            if (current) { setFacilities([]); setLoadState("incomplete"); }
            return;
          }
        } while (cursor && !controller.signal.aborted);
        if (current && !controller.signal.aborted) {
          setFacilities(collected);
          setLoadState(collected.length ? "ready" : "empty");
        }
      } catch (error) {
        if (!current || controller.signal.aborted) return;
        setFacilities([]);
        setApiError(error instanceof Error ? error.message : "机构数据加载失败，请稍后重试");
        setLoadState("error");
      }
    }, 300);
    return () => {
      current = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [viewport, category, region]);

  useEffect(() => {
    const query = search.trim();
    if (!query || !isRegionCodeValid(region)) return;
    const controller = new AbortController();
    let current = true;
    const timer = window.setTimeout(async () => {
      try {
        const params = new URLSearchParams({ q: query, match: "prefix", limit: "20" });
        if (category) params.set("category", category);
        if (region.trim()) params.set("region", region.trim());
        const response = await fetch(`/api/search?${params.toString()}`, { signal: controller.signal });
        const payload = await readJson(response);
        if (!response.ok) throw new Error(messageFrom(payload, "搜索暂时不可用"));
        const rows = Array.isArray(payload.data) ? payload.data as PublicFacility[] : [];
        if (current && !controller.signal.aborted) {
          setSearchResults(rows);
          setSearchState(rows.length ? "ready" : "empty");
        }
      } catch {
        if (!current || controller.signal.aborted) return;
        setSearchResults([]);
        setSearchState("error");
      }
    }, 300);
    return () => { current = false; window.clearTimeout(timer); controller.abort(); };
  }, [search, category, region]);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    let current = true;
    void fetch(`/api/facilities/${encodeURIComponent(selectedId)}`, { signal: controller.signal }).then(async (response) => {
      const payload = await readJson(response);
      if (!response.ok) throw new Error(response.status === 404 ? "该机构详情暂不可用" : messageFrom(payload, "详情加载失败，请稍后重试"));
      return payload.data as PublicFacility;
    }).then((facility) => {
      if (current && !controller.signal.aborted) setDetail(facility);
    }).catch((error: unknown) => {
      if (current && !controller.signal.aborted) setDetailError(error instanceof Error ? error.message : "详情加载失败");
    }).finally(() => {
      if (current && !controller.signal.aborted) setDetailLoading(false);
    });
    return () => { current = false; controller.abort(); };
  }, [selectedId]);

  const selectFacility = (facility: PublicFacility) => {
    selectedForMap(facility.id);
    if (Number.isFinite(facility.longitude) && Number.isFinite(facility.latitude)) mapControllerRef.current?.flyTo(facility.longitude, facility.latitude);
    setSearch("");
    setSearchResults([]);
    setSearchState("idle");
  };

  const changeSearch = (value: string) => {
    setSearch(value);
    if (!value.trim()) {
      setSearchResults([]);
      setSearchState("idle");
    } else {
      setSearchResults([]);
      setSearchState("loading");
    }
  };
  const changeCategory = (value: string) => {
    setCategory(value);
    if (viewport && viewport.zoom >= MIN_FACILITY_DETAIL_ZOOM) {
      setFacilities([]);
      setLoadState("loading");
    }
    clearSelection();
    if (search.trim()) {
      setSearchResults([]);
      setSearchState("loading");
    }
  };
  const changeRegion = (value: string) => {
    setRegion(value);
    clearSelection();
    if (!isRegionCodeValid(value)) {
      setFacilities([]);
      setLoadState("region-invalid");
      setSearchResults([]);
      setSearchState("invalid");
    } else {
      if (viewport && viewport.zoom >= MIN_FACILITY_DETAIL_ZOOM) {
        setFacilities([]);
        setLoadState("loading");
      }
      if (search.trim()) {
        setSearchResults([]);
        setSearchState("loading");
      }
    }
  };

  let statusMessage: string | null = null;
  if (publishedFacilityCount === 0) statusMessage = "当前暂无已发布机构数据";
  else if (loadState === "region-invalid") statusMessage = "地区代码需为 2、4 或 6 位数字";
  else if (loadState === "zoom") statusMessage = "放大地图查看附近眼科医疗资源";
  else if (loadState === "loading") statusMessage = "正在加载当前视窗机构…";
  else if (loadState === "empty") statusMessage = "当前视窗内暂无已发布机构";
  else if (loadState === "too-large") statusMessage = "当前区域较大，请放大地图后查看机构";
  else if (loadState === "incomplete") statusMessage = "当前区域机构较多，请继续放大地图";
  else if (loadState === "error") statusMessage = apiError ?? "机构数据加载失败，请稍后重试";

  return (
    <main className="eye-map-page">
      <header className="eye-map__header">
        <div>
          <p className="eye-map__eyebrow">医疗资源 · 地图浏览</p>
          <h1>全国眼科医疗资源地图</h1>
          <p className="eye-map__disclaimer">信息供查询，实际门诊与服务请以医院官方信息为准。</p>
        </div>
        <LocationControl />
      </header>
      <div className="eye-map__workspace">
        <aside className="eye-map__sidebar" aria-label="医院搜索与列表">
          <SearchAndFilters categories={categories} category={category} region={region} search={search} onCategoryChange={changeCategory} onRegionChange={changeRegion} onSearchChange={changeSearch} />
          {search.trim() && <section className="eye-map__search-results" aria-label="搜索结果" aria-live="polite">
            {searchState === "loading" && <p>正在搜索…</p>}
            {searchState === "empty" && <p>没有找到匹配的机构</p>}
            {searchState === "error" && <p role="alert">搜索暂时不可用，请稍后重试</p>}
            {searchState === "invalid" && <p role="alert">地区代码需为 2、4 或 6 位数字</p>}
            {searchResults.map((facility) => <button key={facility.id} type="button" className="eye-map__search-result" onClick={() => selectFacility(facility)}>
              <strong>{facility.name}</strong><span>{facility.address}</span><span>{facility.region.name}</span>
            </button>)}
          </section>}
          <div className="eye-map__status" aria-live="polite">
            {statusMessage && <p role={loadState === "error" ? "alert" : "status"}>{statusMessage}</p>}
            {basemapError && <p role="alert">地图画布加载失败；机构列表仍可使用。</p>}
            {loadState === "error" && <button type="button" onClick={() => { if (viewport) setViewport({ ...viewport }); }}>重新加载</button>}
          </div>
          <FacilityList facilities={facilities} selectedId={selectedId} labels={labels} onSelect={selectFacility} />
          <p className="eye-map__coverage-note">仅展示当前视窗已发布且可公开查询的机构。</p>
        </aside>
        <div className="eye-map__map-column">
          <MapCanvas facilities={facilities} selectedId={selectedId} onController={receiveController} onViewport={changeViewport} onSelectFacility={selectedForMap} onClearSelection={clearSelection} onError={mapError} />
          <FacilityDetailPanel facility={detail} loading={detailLoading} error={detailError} labels={labels} onClose={clearSelection} />
        </div>
      </div>
    </main>
  );
}
