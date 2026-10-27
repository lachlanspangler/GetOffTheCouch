// Regression tests for the pre-render → hydrate boot (code review, 2026-10-16): hydration never patches attributes,
// so the first client render must match the server HTML exactly.
import { hydrate } from "preact";
import renderToString from "preact-render-to-string";
import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { App } from "../src/app";
import { inlineFor, render } from "../src/entry-server";
import { isInline, memo, record, release, replay, routeSig, setRenderSig } from "../src/lib/partial";
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

// I-117: pre-rendered pages inline only the events they show plus the whole-feed values they computed. Hydrating
// from that partial data must reproduce the server HTML exactly, and replay must stop once the route moves.
describe("inline first-render data", () => {
  const pages = ["/demoville/", "/demoville/this-weekend/", "/demoville/concerts/", "/demoville/deadlines/"];

  it.skipIf(!haveDemo).each(pages)("hydrates %s from the inline data alone", (path) => {
    const index = JSON.parse(readFileSync(`${D}index.json`, "utf8"));
    const feed = JSON.parse(readFileSync(`${D}cities/demoville.json`, "utf8"));
    const now = new Date(index.generated_at);
    const full = render(path, index, feed, now);
    const res = inlineFor(path, index, feed, now, full);
    expect(res.json, `no exact inline data for ${path}`).not.toBeNull();
    if (!res.json) return;
    const data = JSON.parse(res.json); // exactly what the browser parses out of the page
    expect(data.feed.events.length).toBeLessThan(feed.events.length);
    const el = document.createElement("div");
    el.innerHTML = full.html;
    document.body.appendChild(el);
    replay(data.feed, data.sig, data.memo);
    expect(isInline(data.feed)).toBe(true);
    hydration.active = true;
    hydrate(<App initial={{ index, feed: data.feed, route: parsePath(path, ""), now }} />, el);
    hydration.active = false;
    const fresh = document.createElement("div");
    fresh.innerHTML = full.html;
    expect(links(el)).toEqual(links(fresh));
    expect(el.textContent).toEqual(fresh.textContent);
    el.remove();
    release(data.feed);
  });

  it.skipIf(!haveDemo)("an event page inlines its own event in full", () => {
    const index = JSON.parse(readFileSync(`${D}index.json`, "utf8"));
    const feed = JSON.parse(readFileSync(`${D}cities/demoville.json`, "utf8"));
    const now = new Date(index.generated_at);
    const e = feed.events.find((x: { start: string }) => new Date(x.start) > now);
    const path = `/demoville/events/${e.id.replace(/^evt_/, "")}/`;
    const full = render(path, index, feed, now);
    expect(full.status).toBe(200);
    const res = inlineFor(path, index, feed, now, full);
    expect(res.json).not.toBeNull();
    const mine = JSON.parse(res.json!).feed.events.find((x: { id: string }) => x.id === e.id);
    expect(mine).toEqual(e);
  });

  it("replays only on the recorded route, and never for a full feed", () => {
    const ev = (id: string) => ({ id, title: id }) as unknown as import("../src/lib/types").Event;
    const feed = { city: "t", events: [ev("evt_a"), ev("evt_b")] } as unknown as import("../src/lib/types").CityFeed;
    const a = routeSig(parsePath("/t/", ""));
    const b = routeSig(parsePath("/t/concerts/", ""));
    const values = record(feed);
    setRenderSig(a);
    expect(memo(feed, "n", () => feed.events.length)).toBe(2);
    expect(memo(feed, "first", () => [{ event: feed.events[0], more: 3 }])[0].event).toBe(feed.events[0]);
    release(feed);
    expect(values.first).toEqual([{ event: { $e: "evt_a" }, more: 3 }]);
    const part = { ...feed, events: [ev("evt_a")] };
    replay(part, a, values);
    expect(memo(part, "n", () => -1)).toBe(2);
    expect(memo<{ event: unknown }[]>(part, "first", () => [])[0].event).toBe(part.events[0]); // references resolve to the partial feed
    setRenderSig(b);
    expect(memo(part, "n", () => -1)).toBe(-1); // another page: compute
    setRenderSig(a);
    expect(memo(feed, "n", () => -2)).toBe(-2); // the full feed isn't in replay mode
    const gone = { ...feed, events: [] };
    replay(gone, a, values);
    expect(memo(gone, "first", () => "computed")).toBe("computed"); // a referenced event is missing: compute
  });
});
