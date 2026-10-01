import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/lib/public-api/repository.db.test.ts", "src/lib/admin/repository.db.test.ts"],
  },
});
