import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { EyeHospitalsClient } from "./eye-hospitals-client";

const mapHarness = vi.hoisted(() => ({
  onViewport: undefined as undefined | ((viewport: { bbox: [number, number, number, number]; zoom: number }) => void),
  onSelect: undefined as undefined | ((id: string) => void),
  setFacilities: vi.fn(),
  setUserLocation: vi.fn(),
  flyTo: vi.fn(),
}));

vi.mock("../../lib/map/map-adapter", () => ({
  initializeFacilityMap: vi.fn(async (_container: HTMLElement, _config: unknown, callbacks: { onViewport: typeof mapHarness.onViewport; onSelectFacility: typeof mapHarness.onSelect }) => {
    mapHarness.onViewport = callbacks.onViewport;
    mapHarness.onSelect = callbacks.onSelectFacility;
    return {
      setFacilities: mapHarness.setFacilities,
      setUserLocation: mapHarness.setUserLocation,
      flyTo: mapHarness.flyTo,
      destroy: vi.fn(),
    };
  }),
}));

const facility = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "北京眼科测试医院",
  category: "eye_specialty_hospital",
  address: "北京市东城区测试路 1 号",
  region: { adcode: "110101", name: "北京市东城区" },
  hospitalLevel: "三级",
  hospitalGrade: null,
  longitude: 116.4,
  latitude: 39.9,
  ophthalmology: { status: "verified", evidenceCount: 4 },
  attribution: [{ name: "官方公开信息", url: "https://example.gov.cn/hospital", updatedAt: "2026-09-01" }],
  lastVerifiedAt: "2026-09-10T00:00:00.000Z",
  legalRepresentative: "不应展示",
  internalEvidenceCount: 999,
};

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function categories() {
  return response({ data: [{ id: "eye_specialty_hospital", label: "眼科专科医院" }, { id: "unknown", label: "待核验" }], meta: { publishedFacilityCount: 1 }, error: null });
}

function viewport(bbox: [number, number, number, number] = [116.2, 39.7, 116.6, 40.1], zoom = 12) {
  mapHarness.onViewport?.({ bbox, zoom });
}

describe("EyeHospitalsClient", () => {
  beforeEach(() => {
    mapHarness.onViewport = undefined;
    mapHarness.onSelect = undefined;
    mapHarness.setFacilities.mockClear();
    mapHarness.setUserLocation.mockClear();
    mapHarness.flyTo.mockClear();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/facilities") return response({ data: [], meta: { nextCursor: null }, error: null });
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("loads categories and remains usable before the minimum detail zoom", async () => {
    render(<EyeHospitalsClient />);
    expect(await screen.findByText("放大地图查看附近眼科医疗资源")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "机构类型" })).toHaveTextContent("眼科专科医院");
    expect(screen.getByText("信息供查询，实际门诊与服务请以医院官方信息为准。"))
      .toBeInTheDocument();
  });

  it("shows the dataset-wide empty state when the published count is zero", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return response({ data: [{ id: "unknown", label: "待核验" }], meta: { publishedFacilityCount: 0 }, error: null });
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
    render(<EyeHospitalsClient />);
    expect(await screen.findByText("当前暂无已发布机构数据")).toBeInTheDocument();
  });

  it("suppresses detail requests below the API minimum zoom", async () => {
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport([-180, -80, 180, 80], 3);
    expect(await screen.findByText("放大地图查看附近眼科医疗资源")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/facilities?"), expect.anything());
  });

  it("loads viewport pages, links list selection to the map, and never renders internal fields", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/facilities") return response({ data: [facility], meta: { nextCursor: null }, error: null });
      if (url.pathname.endsWith(`/${facility.id}`)) return response({ data: facility, error: null });
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport();
    const item = await screen.findByRole("button", { name: /北京眼科测试医院/ });
    fireEvent.click(item);
    expect(mapHarness.flyTo).toHaveBeenCalledWith(facility.longitude, facility.latitude);
    expect(await screen.findByRole("dialog", { name: "北京眼科测试医院" })).toBeInTheDocument();
    expect(within(screen.getByRole("dialog")).getByText("已核验眼科信息")).toBeInTheDocument();
    expect(screen.queryByText("不应展示")).not.toBeInTheDocument();
    expect(screen.queryByText("999")).not.toBeInTheDocument();
    const link = screen.getByRole("link", { name: "官方公开信息" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    mapHarness.onSelect?.(facility.id);
    await waitFor(() => expect(mapHarness.setFacilities).toHaveBeenLastCalledWith([facility], facility.id));
    expect(within(item).getByText("北京市东城区测试路 1 号")).toBeInTheDocument();
  });

  it("refetches on category changes and reports oversized viewports", async () => {
    const fetchMock = vi.mocked(fetch);
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/facilities?"), expect.anything()));
    fireEvent.change(screen.getByRole("combobox", { name: "机构类型" }), { target: { value: "eye_specialty_hospital" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("category=eye_specialty_hospital"), expect.anything()));
    vi.mocked(fetch).mockImplementation(async (input) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/facilities") return response({ error: { code: "VIEWPORT_TOO_LARGE", message: "请放大地图后查看医疗机构" } }, 400);
      return response({ data: null, error: { code: "NOT_FOUND" } }, 404);
    });
    viewport([-180, -80, 180, 80], 12);
    expect(await screen.findByText("当前区域较大，请放大地图后查看机构")).toBeInTheDocument();
  });

  it("shows an actionable API error state for server failures", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/facilities") return response({ error: { code: "INTERNAL_ERROR", message: "服务暂不可用" } }, 500);
      return response({ data: [] });
    }));
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport();
    expect(await screen.findByRole("alert")).toHaveTextContent("服务暂不可用");
    expect(screen.getByRole("button", { name: "重新加载" })).toBeInTheDocument();
  });

  it("searches facilities and opens the selected detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/facilities") return response({ data: [], meta: { nextCursor: null }, error: null });
      if (url.pathname === "/api/search") return response({ data: [facility], meta: { nextCursor: null }, error: null });
      if (url.pathname.endsWith(`/${facility.id}`)) return response({ data: facility, error: null });
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport();
    expect(await screen.findByText("当前视窗内暂无已发布机构")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "搜索医院" }), { target: { value: "北京眼科" } });
    expect(await screen.findByRole("button", { name: /北京眼科测试医院/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /北京眼科测试医院/ }));
    expect(await screen.findByRole("dialog", { name: "北京眼科测试医院" })).toBeInTheDocument();
  });

  it("aborts a stale viewport request when the user moves the map", async () => {
    const signals: AbortSignal[] = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return Promise.resolve(categories());
      if (url.pathname === "/api/facilities") {
        const signal = init?.signal as AbortSignal;
        signals.push(signal);
        return new Promise<Response>((_resolve, reject) => signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true }));
      }
      return Promise.resolve(response({ data: [] }));
    }));
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport();
    await waitFor(() => expect(signals).toHaveLength(1), { timeout: 2000 });
    viewport([116.3, 39.8, 116.7, 40.2], 12);
    await waitFor(() => expect(signals).toHaveLength(2), { timeout: 2000 });
    expect(signals[0].aborted).toBe(true);
  });

  it("shows a clear message when a selected facility detail is not found", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/facilities") return response({ data: [facility], meta: { nextCursor: null }, error: null });
      if (url.pathname.endsWith(`/${facility.id}`)) return response({ error: { code: "NOT_FOUND" } }, 404);
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
    render(<EyeHospitalsClient />);
    await screen.findByText("放大地图查看附近眼科医疗资源");
    await waitFor(() => expect(mapHarness.onViewport).toBeTypeOf("function"));
    viewport();
    fireEvent.click(await screen.findByRole("button", { name: /北京眼科测试医院/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("该机构详情暂不可用");
  });

  it("locates only after a user click, queries nearby without accuracy, and keeps the exact point out of browser storage", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) => success({
      coords: { longitude: 116.4, latitude: 39.9, accuracy: 35 } as GeolocationCoordinates,
      timestamp: Date.now(),
    } as GeolocationPosition));
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition, watchPosition: vi.fn() } });
    const nearby = { ...facility, distanceMeters: 620 };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/nearby") return response({ data: [nearby], meta: { count: 1, radiusMeters: 10_000, truncated: true }, error: null });
      if (url.pathname.endsWith(`/${facility.id}`)) return response({ data: facility, error: null });
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
    localStorage.clear();
    sessionStorage.clear();
    render(<EyeHospitalsClient />);
    const locate = await screen.findByRole("button", { name: "定位到我" });
    expect(getCurrentPosition).not.toHaveBeenCalled();
    fireEvent.click(locate);
    expect(getCurrentPosition).toHaveBeenCalledWith(expect.any(Function), expect.any(Function), {
      enableHighAccuracy: false,
      timeout: 10_000,
      maximumAge: 300_000,
    });
    expect(await screen.findByText("620 m")).toBeInTheDocument();
    expect(screen.getByText("附近机构较多，可缩小搜索半径")).toBeInTheDocument();
    await waitFor(() => expect(mapHarness.setFacilities).toHaveBeenCalledWith([nearby], null));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/nearby?"), expect.objectContaining({ signal: expect.any(AbortSignal) })));
    const nearbyRequest = vi.mocked(fetch).mock.calls.find(([input]) => new URL(String(input), "http://localhost").pathname === "/api/nearby");
    expect(nearbyRequest).toBeDefined();
    const url = new URL(String(nearbyRequest?.[0]), "http://localhost");
    expect(url.searchParams.get("lat")).toBe("39.9");
    expect(url.searchParams.get("lng")).toBe("116.4");
    expect(url.searchParams.has("accuracy")).toBe(false);
    expect(mapHarness.setUserLocation).toHaveBeenCalledWith({ longitude: 116.4, latitude: 39.9 });
    expect(mapHarness.flyTo).toHaveBeenCalledWith(116.4, 39.9);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).not.toContain("39.9");
    fireEvent.click(screen.getByRole("button", { name: /北京眼科测试医院/ }));
    expect(await screen.findByRole("dialog", { name: "北京眼科测试医院" })).toBeInTheDocument();
  });

  it("shows denied and retry guidance without requesting location again automatically", async () => {
    const getCurrentPosition = vi.fn((_success: PositionCallback, error: PositionErrorCallback) => error({ code: 1, message: "denied" } as GeolocationPositionError));
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition } });
    render(<EyeHospitalsClient />);
    fireEvent.click(await screen.findByRole("button", { name: "定位到我" }));
    expect(await screen.findByText("定位权限未开启，你仍可以搜索或手动浏览地图。")).toBeInTheDocument();
    expect(screen.getByText("可通过地区筛选或拖动地图继续浏览")).toBeInTheDocument();
    expect(getCurrentPosition).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "重新尝试定位" }));
    expect(getCurrentPosition).toHaveBeenCalledTimes(2);
  });

  it("exposes the requesting state until the browser responds", async () => {
    let complete: PositionCallback | undefined;
    const getCurrentPosition = vi.fn((success: PositionCallback) => { complete = success; });
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition } });
    render(<EyeHospitalsClient />);
    fireEvent.click(await screen.findByRole("button", { name: "定位到我" }));
    expect(screen.getByRole("button", { name: "正在获取位置…" })).toBeDisabled();
    complete?.({ coords: { longitude: 116.4, latitude: 39.9, accuracy: 50 } as GeolocationCoordinates, timestamp: Date.now() } as GeolocationPosition);
    expect(await screen.findByRole("button", { name: "已定位" })).toBeEnabled();
  });

  it.each([
    ["timeout", 3, "定位超时，请重试"],
    ["unavailable", 2, "当前设备无法提供位置"],
  ])("shows the %s state and leaves manual browsing available", async (_name, code, message) => {
    const getCurrentPosition = vi.fn((_success: PositionCallback, error: PositionErrorCallback) => error({ code, message: "browser error" } as GeolocationPositionError));
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition } });
    render(<EyeHospitalsClient />);
    fireEvent.click(await screen.findByRole("button", { name: "定位到我" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByText("可通过地区筛选或拖动地图继续浏览")).toBeInTheDocument();
  });

  it("reports unsupported geolocation while keeping the map browser usable", async () => {
    vi.stubGlobal("navigator", { ...navigator, geolocation: undefined });
    render(<EyeHospitalsClient />);
    fireEvent.click(await screen.findByRole("button", { name: "定位到我" }));
    expect(await screen.findByText("当前浏览器不支持定位")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "机构类型" })).toBeEnabled();
    expect(screen.getByText("可通过地区筛选或拖动地图继续浏览")).toBeInTheDocument();
  });

  it("requeries on radius and category changes and aborts each stale nearby request", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) => success({ coords: { longitude: 116.4, latitude: 39.9, accuracy: 20 } as GeolocationCoordinates, timestamp: Date.now() } as GeolocationPosition));
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition } });
    const signals: AbortSignal[] = [];
    const urls: URL[] = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return Promise.resolve(categories());
      if (url.pathname === "/api/nearby") {
        urls.push(url);
        const signal = init?.signal as AbortSignal;
        signals.push(signal);
        return new Promise<Response>((_resolve, reject) => signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true }));
      }
      return Promise.resolve(response({ data: [], meta: { nextCursor: null }, error: null }));
    }));
    render(<EyeHospitalsClient />);
    fireEvent.click(await screen.findByRole("button", { name: "定位到我" }));
    await waitFor(() => expect(signals).toHaveLength(1));
    expect(urls[0].searchParams.get("radius")).toBe("10000");
    fireEvent.change(screen.getByRole("combobox", { name: "附近搜索半径" }), { target: { value: "5000" } });
    await waitFor(() => expect(signals).toHaveLength(2));
    expect(signals[0].aborted).toBe(true);
    expect(urls[1].searchParams.get("radius")).toBe("5000");
    fireEvent.change(screen.getByRole("combobox", { name: "机构类型" }), { target: { value: "eye_specialty_hospital" } });
    await waitFor(() => expect(signals).toHaveLength(3));
    expect(signals[1].aborted).toBe(true);
    expect(urls[2].searchParams.get("category")).toBe("eye_specialty_hospital");
  });

  it("shows distinct empty and nearby API failure states without replacing the viewport browser", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) => success({ coords: { longitude: 116.4, latitude: 39.9, accuracy: 25 } as GeolocationCoordinates, timestamp: Date.now() } as GeolocationPosition));
    vi.stubGlobal("navigator", { ...navigator, geolocation: { getCurrentPosition } });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/nearby") return response({ data: [], meta: { count: 0, radiusMeters: 10_000, truncated: false }, error: null });
      return response({ data: [], meta: { nextCursor: null }, error: null });
    }));
    render(<EyeHospitalsClient />);
    fireEvent.click(await screen.findByRole("button", { name: "定位到我" }));
    expect(await screen.findByText("附近 10 公里暂无已发布眼科医疗机构")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "机构类型" })).toBeEnabled();

    vi.mocked(fetch).mockImplementation(async (input) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname === "/api/meta/categories") return categories();
      if (url.pathname === "/api/nearby") return response({ error: { code: "INTERNAL_ERROR" } }, 500);
      return response({ data: [], meta: { nextCursor: null }, error: null });
    });
    fireEvent.change(screen.getByRole("combobox", { name: "附近搜索半径" }), { target: { value: "5000" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("附近机构加载失败，请稍后重试");
    expect(screen.getByRole("combobox", { name: "机构类型" })).toBeEnabled();
    expect(screen.getByRole("combobox", { name: "附近搜索半径" })).toBeEnabled();
  });
});
