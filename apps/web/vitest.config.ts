import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: [
      "src/lib/public-api/handlers.test.ts",
      "src/lib/public-api/nearby.test.ts",
      "src/features/**/*.test.tsx",
      "src/lib/map/**/*.test.ts",
      "src/lib/admin/**/*.test.ts",
      "src/app/hospitals/**/*.test.tsx",
    ],
    exclude: ["**/*.db.test.ts", "**/node_modules/**", "**/.git/**"],
    setupFiles: ["./src/test/setup.ts"],
    maxWorkers: 1,
  },
});
