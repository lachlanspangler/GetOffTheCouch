// Data loading. The pipeline writes static JSON; the dashboard only reads it.
// ?demo=1 switches to clearly-labeled demo data in /demo (never mixed with real data).
import type { CityDetails } from "./details.generated";
import type { CityFeed, HealthDoc, Index } from "./types";

const base = import.meta.env.BASE_URL.replace(/\/$/, "");

// ?demo=1 sticks for the tab (sessionStorage) so in-app navigation keeps showing demo data; ?demo=0 clears it.
const DEMO = (() => {
  if (typeof location === "undefined") return false;
  try {
    const q = new URLSearchParams(location.search).get("demo");
    if (q === "1") sessionStorage.setItem("gotc:demo", "1");
    if (q === "0") sessionStorage.removeItem("gotc:demo");
    return sessionStorage.getItem("gotc:demo") === "1";
  } catch {
    return new URLSearchParams(location.search).get("demo") === "1";
  }
})();

export function isDemo(): boolean {
  return DEMO;
}

function root(): string {
  return `${base}/${isDemo() ? "demo" : "data"}`;
}

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${root()}/${path}`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

export const loadIndex = () => getJSON<Index>("index.json");
export const loadCity = (slug: string) => getJSON<CityFeed>(`cities/${slug}.json`);
export const loadHealth = () => getJSON<HealthDoc>("health.json");

const detailCache = new Map<string, Promise<CityDetails>>();

/** Provenance + full descriptions, fetched once per city the first time a card is opened. */
export function loadDetails(slug: string): Promise<CityDetails> {
  let p = detailCache.get(slug);
  if (!p) {
    p = getJSON<CityDetails>(`cities/${slug}.details.json`);
    p.catch(() => detailCache.delete(slug));
    detailCache.set(slug, p);
  }
  return p;
}
