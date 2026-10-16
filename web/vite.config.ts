import preact from "@preact/preset-vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./", // works on GitHub Pages project sites and any static host
  plugins: [preact()],
  build: { target: "es2020", sourcemap: true },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
  },
});
