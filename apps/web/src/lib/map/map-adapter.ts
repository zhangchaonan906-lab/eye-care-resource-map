import type { FeatureCollection, Point } from "geojson";
import type { GeoJSONSource } from "maplibre-gl";
import type { PublicFacility } from "../public-api/types";
import type { BasemapConfig } from "../basemap/types";

export type Viewport = { bbox: [number, number, number, number]; zoom: number };
export type FacilityMapController = {
  setFacilities: (facilities: PublicFacility[], selectedId: string | null) => void;
  flyTo: (longitude: number, latitude: number) => void;
  destroy: () => void;
};

export async function initializeFacilityMap(
  container: HTMLElement,
  config: BasemapConfig,
  callbacks: { onViewport: (viewport: Viewport) => void; onSelectFacility: (id: string) => void; onClearSelection: () => void },
): Promise<FacilityMapController> {
  const { Map } = await import("maplibre-gl");
  const map = new Map({
    container,
    style: config.styleObject,
    center: [105, 35],
    zoom: 4,
    minZoom: 2,
    maxZoom: 24,
    attributionControl: false,
  });
  let latest: FeatureCollection<Point, { id: string; name: string }> = { type: "FeatureCollection", features: [] };
  let selectedId: string | null = null;

  const emitViewport = () => {
    const bounds = map.getBounds();
    callbacks.onViewport({
      bbox: [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
      zoom: map.getZoom(),
    });
  };

  map.on("load", () => {
    map.addSource("facilities", { type: "geojson", data: latest, cluster: true, clusterMaxZoom: 17, clusterRadius: 48 });
    map.addLayer({
      id: "facility-clusters",
      type: "circle",
      source: "facilities",
      filter: ["has", "point_count"],
      paint: { "circle-color": "#166b79", "circle-radius": ["step", ["get", "point_count"], 18, 20, 23, 100, 29], "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 },
    });
    map.addLayer({
      id: "facility-cluster-count",
      type: "symbol",
      source: "facilities",
      filter: ["has", "point_count"],
      layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12 },
      paint: { "text-color": "#ffffff" },
    });
    map.addLayer({
      id: "facility-points",
      type: "circle",
      source: "facilities",
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-color": ["case", ["==", ["get", "id"], selectedId ?? ""], "#d14d52", "#1e8794"],
        "circle-radius": ["case", ["==", ["get", "id"], selectedId ?? ""], 9, 7],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
      },
    });
    map.on("click", "facility-points", (event) => {
      const id = event.features?.[0]?.properties?.id;
      if (typeof id === "string") callbacks.onSelectFacility(id);
    });
    map.on("click", "facility-clusters", (event) => {
      const feature = map.queryRenderedFeatures(event.point, { layers: ["facility-clusters"] })[0];
      const clusterId = feature?.properties?.cluster_id;
      const source = map.getSource("facilities") as GeoJSONSource | undefined;
      if (typeof clusterId === "number" && source && feature) {
        const coordinates = feature.geometry.type === "Point" ? feature.geometry.coordinates : null;
        void source.getClusterExpansionZoom(clusterId).then((zoom) => {
          if (coordinates) map.easeTo({ center: [coordinates[0], coordinates[1]], zoom });
        }).catch(() => undefined);
      }
    });
    map.on("click", (event) => {
      if (map.queryRenderedFeatures(event.point, { layers: ["facility-points", "facility-clusters"] }).length === 0) callbacks.onClearSelection();
    });
    map.on("moveend", emitViewport);
    map.on("zoomend", emitViewport);
    emitViewport();
  });

  return {
    setFacilities(facilities, nextSelectedId) {
      selectedId = nextSelectedId;
      latest = {
        type: "FeatureCollection",
        features: facilities.map((facility) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [facility.longitude, facility.latitude] },
          properties: { id: facility.id, name: facility.name },
        })),
      };
      const source = map.getSource("facilities") as GeoJSONSource | undefined;
      source?.setData(latest);
      if (map.getLayer("facility-points")) {
        map.setPaintProperty("facility-points", "circle-color", ["case", ["==", ["get", "id"], selectedId ?? ""], "#d14d52", "#1e8794"]);
        map.setPaintProperty("facility-points", "circle-radius", ["case", ["==", ["get", "id"], selectedId ?? ""], 9, 7]);
      }
    },
    flyTo(longitude, latitude) {
      map.flyTo({ center: [longitude, latitude], zoom: Math.max(map.getZoom(), 13), duration: 500 });
    },
    destroy() { map.remove(); },
  };
}
