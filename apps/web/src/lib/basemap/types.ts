import type { StyleSpecification } from "maplibre-gl";

export type BasemapConfig = {
  styleObject: StyleSpecification;
  attribution: string;
  coordinateSystem: "WGS84";
  environment: "development-placeholder" | "approved-production";
};
