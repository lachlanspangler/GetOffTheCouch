// Regression tests for the pre-render → hydrate boot (code review, 2026-10-16): hydration never patches attributes,
// so the first client render must match the server HTML exactly.
import { hydrate } from "preact";
import renderToString from "preact-render-to-string";
import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { App } from "../src/app";
import { parsePath } from "../src/lib/router";
import { canHydrate, hydration } from "../src/lib/store";

const D = `${process.cwd()}/public/demo/`;
const haveDemo = existsSync(`${D}index.json`); // `gotc demo` writes it (make check and CI run it first)
const links = (r: Element) => [...r.querySelectorAll("a[href]")].map((a) => `${a.getAttribute("href")}|${a.textContent?.trim()}`);

describe("hydration", () => {
  it("only hydrates clean pre-rendered URLs", () => {
    expect(canHydrate({ hash: "", search: "" }, false)).toBe(true);
    expect(canHydrate({ hash: "", search: "?when=weekend" }, false)).toBe(false);
    expect(canHydrate({ hash: "#/nyc/feed", search: "" }, false)).toBe(false);
    expect(canHydrate({ hash: "", search: "" }, true)).toBe(false);
  });

  it.skipIf(!haveDemo)("matches the server HTML even when this device has saved items and dismissals", () => {
    const index = JSON.parse(readFileSync(`${D}index.json`, "utf8"));
    const feed = JSON.parse(readFileSync(`${D}cities/demoville.json`, "utf8"));
    const now = new Date(index.generated_at);
    const route = parsePath("/demoville/", "");
    const html = renderToString(<App initial={{ index, feed, route, now }} />);
    // this device has history the server never saw
    localStorage.setItem("gotc:saved:demoville", JSON.stringify([feed.events[0].id]));
    localStorage.setItem("gotc:dismissed:v1", JSON.stringify({ ids: { [feed.events[1].id]: Date.now() } }));
    const el = document.createElement("div");
    el.innerHTML = html;
    document.body.appendChild(el);
    hydration.active = true;
    hydrate(<App initial={{ index, feed, route, now }} />, el);
    hydration.active = false;
    const fresh = document.createElement("div");
    fresh.innerHTML = html;
    expect(links(el)).toEqual(links(fresh));
    localStorage.clear();
  });
});
