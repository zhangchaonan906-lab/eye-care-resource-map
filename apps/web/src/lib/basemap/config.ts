import type { BasemapConfig } from "./types";

/** Local blank canvas only. Replace after the provider, license and attribution are approved. */
export const basemapConfig: BasemapConfig = {
  environment: "development-placeholder",
  coordinateSystem: "WGS84",
  attribution: "开发占位底图 · 无在线瓦片",
  styleObject: {
    version: 8,
    name: "Eye Care development placeholder",
    sources: {},
    layers: [{ id: "background", type: "background", paint: { "background-color": "#eef3f6" } }],
  },
};
