import { beforeEach, describe, expect, it, vi } from "vitest";
import { basemapConfig } from "../basemap/config";
import type { PublicFacility } from "../public-api/types";
import { initializeFacilityMap } from "./map-adapter";

const harness = vi.hoisted(() => ({
  handlers: new Map<string, (...args: unknown[]) => void>(),
  options: undefined as Record<string, unknown> | undefined,
  addedSources: [] as Array<{ id: string; options: Record<string, unknown> }>,
  sources: new Map<string, { setData: ReturnType<typeof vi.fn>; getClusterExpansionZoom: ReturnType<typeof vi.fn> }>(),
  addedLayers: [] as Array<Record<string, unknown>>,
  setData: vi.fn(),
  easeTo: vi.fn(),
  flyTo: vi.fn(),
  removed: vi.fn(),
}));

vi.mock("maplibre-gl", async () => {
  const actual = await vi.importActual<typeof import("maplibre-gl")>("maplibre-gl");
  return {
    ...actual,
    Map: class {
      constructor(options: Record<string, unknown>) { harness.options = options; }
      on(event: string, layerOrListener: string | ((...args: unknown[]) => void), listener?: (...args: unknown[]) => void) {
        harness.handlers.set(`${event}:${typeof layerOrListener === "string" ? layerOrListener : ""}`, typeof layerOrListener === "function" ? layerOrListener : listener!);
      }
      addSource(id: string, options: Record<string, unknown>) { harness.addedSources.push({ id, options }); harness.sources.set(id, { setData: harness.setData, getClusterExpansionZoom: vi.fn(async () => 9) }); }
      addLayer(layer: Record<string, unknown>) { harness.addedLayers.push(layer); }
      getSource(id: string) { return harness.sources.get(id); }
      getLayer() { return true; }
      setPaintProperty() { return undefined; }
      getBounds() { return { getWest: () => 116, getSouth: () => 39, getEast: () => 116.5, getNorth: () => 40 }; }
      getZoom() { return 12; }
      queryRenderedFeatures() { return [{ properties: { cluster_id: 7 }, geometry: { type: "Point", coordinates: [116.2, 39.8] } }]; }
      easeTo(options: unknown) { harness.easeTo(options); }
      flyTo(options: unknown) { harness.flyTo(options); }
      remove() { harness.removed(); }
    },
  };
});

const sampleFacility = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "示例眼科医院",
  category: "eye_specialty_hospital",
  address: "地址",
  region: { adcode: "110101", name: "东城区" },
  hospitalLevel: null,
  hospitalGrade: null,
  longitude: 116.4,
  latitude: 39.9,
  ophthalmology: { status: "verified", evidenceCount: 1 },
  attribution: [],
  lastVerifiedAt: "2026-09-01T00:00:00.000Z",
} satisfies PublicFacility;

describe("MapLibre adapter", () => {
  beforeEach(() => {
    harness.handlers.clear();
    harness.options = undefined;
    harness.addedSources = [];
    harness.sources.clear();
    harness.addedLayers = [];
    harness.setData.mockClear();
    harness.easeTo.mockClear();
    harness.flyTo.mockClear();
    harness.removed.mockClear();
  });

  it("uses a local WGS84 placeholder style and clusters complete viewport GeoJSON", async () => {
    const viewport = vi.fn();
    const select = vi.fn();
    const clear = vi.fn();
    const map = await initializeFacilityMap(document.createElement("div"), basemapConfig, {
      onViewport: viewport,
      onSelectFacility: select,
      onClearSelection: clear,
    });
    expect(basemapConfig.environment).toBe("development-placeholder");
    expect(basemapConfig.coordinateSystem).toBe("WGS84");
    expect(basemapConfig.styleObject.sources).toEqual({});
    expect(JSON.stringify(harness.options)).not.toMatch(/https?:/);

    harness.handlers.get("load:")?.();
    expect(harness.addedSources.map(({ id }) => id)).toEqual(["facilities", "user-location"]);
    expect(harness.addedSources[0].options).toMatchObject({ cluster: true, clusterMaxZoom: 17, clusterRadius: 48 });
    expect(harness.addedSources[1].options).toMatchObject({ type: "geojson" });
    expect(harness.addedLayers.map((layer) => layer.id)).toEqual(["facility-clusters", "user-location-halo", "user-location-point", "facility-cluster-count", "facility-points"]);

    map.setFacilities([sampleFacility], sampleFacility.id);
    expect(harness.sources.get("facilities")?.setData).toHaveBeenCalledWith(expect.objectContaining({
      type: "FeatureCollection",
      features: [expect.objectContaining({ geometry: { type: "Point", coordinates: [116.4, 39.9] } })],
    }));
    map.setUserLocation({ longitude: 116.41, latitude: 39.91 });
    expect(harness.sources.get("user-location")?.setData).toHaveBeenCalledWith({
      type: "FeatureCollection",
      features: [{ type: "Feature", geometry: { type: "Point", coordinates: [116.41, 39.91] }, properties: {} }],
    });
    map.setUserLocation(null);
    expect(harness.sources.get("user-location")?.setData).toHaveBeenLastCalledWith({ type: "FeatureCollection", features: [] });
    harness.handlers.get("click:facility-points")?.({ features: [{ properties: { id: sampleFacility.id } }] });
    expect(select).toHaveBeenCalledWith(sampleFacility.id);
    harness.handlers.get("click:facility-clusters")?.({ point: { x: 1, y: 1 } });
    await Promise.resolve();
    expect(harness.easeTo).toHaveBeenCalledWith({ center: [116.2, 39.8], zoom: 9 });
    map.flyTo(116.4, 39.9);
    expect(harness.flyTo).toHaveBeenCalledWith({ center: [116.4, 39.9], zoom: 13, duration: 500 });
    map.destroy();
    expect(harness.removed).toHaveBeenCalledOnce();
  });
});
