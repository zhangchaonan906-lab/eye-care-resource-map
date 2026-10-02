import { copyFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const source = resolve(root, "node_modules/maplibre-gl/dist");
const destination = resolve(root, "public/vendor/maplibre-gl");

await mkdir(destination, { recursive: true });
for (const filename of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  await copyFile(resolve(source, filename), resolve(destination, filename));
}
