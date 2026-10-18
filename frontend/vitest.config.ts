import path from "node:path";
import { defineConfig } from "vitest/config";

// Stage C adds React component tests (login/register forms, the auth
// context, the RequireAuth guard), which need a real `document`/DOM --
// hence jsdom as the default environment now. api.test.ts (Stage B) still
// passes under jsdom: it stubs `document`/`fetch` itself via
// vi.stubGlobal, which works the same whether or not a real jsdom
// `document` already exists underneath.
export default defineConfig({
  // Mirrors tsconfig.json's "@/*" -> "./src/*" path mapping -- Vite/Vitest
  // doesn't read tsconfig paths automatically, so component test files
  // that import via "@/..." (matching the rest of the app's convention)
  // need this spelled out here too.
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
