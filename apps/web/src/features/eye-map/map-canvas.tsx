"use client";

import { useEffect, useRef } from "react";
import type { PublicFacility } from "../../lib/public-api/types";
import { basemapConfig } from "../../lib/basemap/config";
import { initializeFacilityMap, type FacilityMapController, type MapLocation, type Viewport } from "../../lib/map/map-adapter";

type Props = {
  facilities: PublicFacility[];
  userLocation: MapLocation | null;
  selectedId: string | null;
  onController: (controller: FacilityMapController | null) => void;
  onViewport: (viewport: Viewport) => void;
  onSelectFacility: (id: string) => void;
  onClearSelection: () => void;
  onError: () => void;
};

export function MapCanvas({ facilities, userLocation, selectedId, onController, onViewport, onSelectFacility, onClearSelection, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<FacilityMapController | null>(null);
  const callbackRef = useRef({ onViewport, onSelectFacility, onClearSelection });
  const latestMapDataRef = useRef({ facilities, selectedId, userLocation });

  useEffect(() => {
    callbackRef.current = { onViewport, onSelectFacility, onClearSelection };
  }, [onViewport, onSelectFacility, onClearSelection]);

  useEffect(() => {
    latestMapDataRef.current = { facilities, selectedId, userLocation };
  }, [facilities, selectedId, userLocation]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let active = true;
    void initializeFacilityMap(container, basemapConfig, {
      onViewport: (viewport) => callbackRef.current.onViewport(viewport),
      onSelectFacility: (id) => callbackRef.current.onSelectFacility(id),
      onClearSelection: () => callbackRef.current.onClearSelection(),
    }).then((controller) => {
      if (!active) {
        controller.destroy();
        return;
      }
      mapRef.current = controller;
      controller.setFacilities(latestMapDataRef.current.facilities, latestMapDataRef.current.selectedId);
      controller.setUserLocation(latestMapDataRef.current.userLocation);
      if (latestMapDataRef.current.userLocation) {
        controller.flyTo(latestMapDataRef.current.userLocation.longitude, latestMapDataRef.current.userLocation.latitude);
      }
      onController(controller);
    }).catch(() => {
      if (active) onError();
    });
    return () => {
      active = false;
      mapRef.current?.destroy();
      mapRef.current = null;
      onController(null);
    };
  }, [onController, onError]);

  useEffect(() => {
    mapRef.current?.setFacilities(facilities, selectedId);
  }, [facilities, selectedId]);

  useEffect(() => {
    mapRef.current?.setUserLocation(userLocation);
  }, [userLocation]);

  return (
    <section className="eye-map__map-region" aria-label="医疗机构地图">
      <div ref={containerRef} className="eye-map__map" data-testid="map-canvas" />
      <div className="eye-map__basemap-badge" aria-label="开发占位底图">开发占位底图</div>
      <div className="eye-map__attribution">{basemapConfig.attribution}</div>
    </section>
  );
}
