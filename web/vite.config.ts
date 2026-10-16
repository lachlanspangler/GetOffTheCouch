import preact from "@preact/preset-vite";
import { copyFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vitest/config";

// GOTC_BASE: "/GetOffTheCouch/" on the GitHub Pages project site, "/" on a custom domain and in dev.
const base = process.env.GOTC_BASE ?? "/";
const origin = process.env.GOTC_SITE_ORIGIN ?? "https://lachlanspangler.github.io";

/** Pages serves 404.html for unknown paths: the app shell routes them client-side (never a blank page). */
function spaFallback(): Plugin {
  return {
    name: "gotc-404",
    apply: "build",
    closeBundle() {
      const dist = resolve(__dirname, "dist");
      copyFileSync(resolve(dist, "index.html"), resolve(dist, "404.html"));
    },
  };
}

export default defineConfig({
  base,
  define: { __SITE_ORIGIN__: JSON.stringify(origin) },
  plugins: [preact(), spaFallback()],
  build: { target: "es2020", sourcemap: process.env.GOTC_SOURCEMAP === "1" },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
    // the offline ranking eval runs as its own step (`npm run eval:rank`, part of `make check`)
    exclude: process.env.GOTC_EVAL ? ["**/node_modules/**"] : ["**/node_modules/**", "tests/rank/eval.test.ts"],
  },
});
