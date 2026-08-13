import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    // Components only. The API contract is proved by the generated types and
    // the backend's own suite; re-asserting it here would test the mock.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
