import { beforeEach, describe, expect, it, vi } from "vitest";
import { basemapConfig } from "../basemap/config";
import type { PublicFacility } from "../public-api/types";
import { initializeFacilityMap } from "./map-adapter";

const harness = vi.hoisted(() => ({
  handlers: new Map<string, (...args: unknown[]) => void>(),
  options: undefined as Record<string, unknown> | undefined,
  addedSource: undefined as { id: string; options: Record<string, unknown> } | undefined,
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
      addSource(id: string, options: Record<string, unknown>) { harness.addedSource = { id, options }; }
      addLayer(layer: Record<string, unknown>) { harness.addedLayers.push(layer); }
      getSource() { return { type: "geojson", setData: harness.setData, getClusterExpansionZoom: vi.fn(async () => 9) }; }
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
    harness.addedSource = undefined;
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
    expect(harness.addedSource?.id).toBe("facilities");
    expect(harness.addedSource?.options).toMatchObject({ cluster: true, clusterMaxZoom: 17, clusterRadius: 48 });
    expect(harness.addedLayers.map((layer) => layer.id)).toEqual(["facility-clusters", "facility-cluster-count", "facility-points"]);

    map.setFacilities([sampleFacility], sampleFacility.id);
    expect(harness.setData).toHaveBeenCalledWith(expect.objectContaining({
      type: "FeatureCollection",
      features: [expect.objectContaining({ geometry: { type: "Point", coordinates: [116.4, 39.9] } })],
    }));
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
