import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/lib/public-api/handlers.test.ts", "src/features/**/*.test.tsx", "src/lib/map/**/*.test.ts"],
    setupFiles: ["./src/test/setup.ts"],
    maxWorkers: 1,
  },
});
