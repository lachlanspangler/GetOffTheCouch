// Data loading. The pipeline writes static JSON; the dashboard only reads it.
// ?demo=1 switches to clearly-labeled demo data in /demo (never mixed with real data).
//
// City data (I-117): cities/<slug>/manifest.json (always revalidated) lists content-hashed week shards. A city
// loads its metadata plus the shards the current view needs (the current and next week first), then the rest in
// idle time. Cities without a manifest (older exports, external mirrors) fall back to the monolithic
// cities/<slug>.json, which the pipeline keeps writing.
import type { CityDetails, EventDetail } from "./details.generated";
import type { CityManifest, ShardRef } from "./manifest.generated";
import type { CityFeed, Event, HealthDoc, Index } from "./types";

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

class HttpError extends Error {
  constructor(
    path: string,
    readonly status: number,
  ) {
    super(`${path}: HTTP ${status}`);
  }
}

// Unhashed files revalidate every time (cheap 304s); hashed shard files can come straight from the HTTP cache.
async function getJSON<T>(path: string, cache: RequestCache = "no-cache"): Promise<T> {
  const r = await fetch(`${root()}/${path}`, { cache });
  if (!r.ok) throw new HttpError(path, r.status);
  return (await r.json()) as T;
}

export const loadIndex = () => getJSON<Index>("index.json");
export const loadHealth = () => getJSON<HealthDoc>("health.json");

interface CityShardDoc {
  city: string;
  key: string;
  events: Event[];
}
interface CityShardDetailsDoc {
  city: string;
  key: string;
  events: Record<string, EventDetail>;
}

/** What a view needs loaded: shards starting before `until` (ms), optionally openings, every upcoming shard, the past. */
export interface Need {
  until: number;
  openings?: boolean;
  all?: boolean; // everything that hasn't ended (calendar, plan)
  past?: boolean; // plus the past weeks (saved items, an ended event's page)
}

const DAY = 86_400_000;

/** Merge order matches the pipeline's export order (start instant, then id), so merged feeds equal the legacy file. */
function byStart(a: Event, b: Event): number {
  return Date.parse(a.start) - Date.parse(b.start) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}

const idle = (fn: () => void) => {
  const w = globalThis as { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number };
  if (w.requestIdleCallback) w.requestIdleCallback(fn, { timeout: 2000 });
  else setTimeout(fn, 30);
};

function saveData(): boolean {
  const c = (globalThis.navigator as { connection?: { saveData?: boolean } } | undefined)?.connection;
  return !!c?.saveData;
}

export class CityData {
  private manifest: Promise<CityManifest | null>;
  private meta: Promise<CityFeed> | null = null;
  private legacy: Promise<CityFeed> | null = null;
  private shards = new Map<string, Promise<Event[]>>();
  private loaded = new Map<string, Event[]>();
  private where = new Map<string, string>(); // event id → shard key (also seeded from inline page hints)
  private idleStarted = false;
  private listeners = new Set<(f: CityFeed, complete: boolean) => void>();
  private retried = false;

  constructor(readonly slug: string) {
    this.manifest = this.fetchManifest();
  }

  private fetchManifest(cache: RequestCache = "no-cache"): Promise<CityManifest | null> {
    return getJSON<CityManifest>(`cities/${this.slug}/manifest.json`, cache).catch((e: unknown) => {
      if (e instanceof HttpError && e.status === 404) return null; // no shards for this city: legacy file
      throw e;
    });
  }

  /** Remember which shard holds an event (pre-rendered pages pass this, so details load without the cards). */
  hint(where: Record<string, string>): void {
    for (const [id, key] of Object.entries(where)) this.where.set(id, key);
  }

  private files = new Map<string, Promise<unknown>>();

  private file(path: string): Promise<unknown> {
    let p = this.files.get(path);
    if (!p) {
      p = getJSON<unknown>(`cities/${this.slug}/${path}`, "default");
      p.catch(() => this.files.delete(path));
      this.files.set(path, p);
    }
    return p;
  }

  /** A deploy replaced the shards between our manifest fetch and a shard fetch: start over once, from a fresh manifest. */
  private restart(e: unknown): boolean {
    if (!(e instanceof HttpError) || e.status !== 404 || this.retried) return false;
    this.retried = true;
    this.manifest = this.fetchManifest("reload");
    this.meta = null;
    this.shards.clear();
    this.loaded.clear();
    return true;
  }

  private shard(ref: ShardRef): Promise<Event[]> {
    let p = this.shards.get(ref.key);
    if (!p) {
      p = (this.file(ref.cards.file) as Promise<CityShardDoc>).then((d) => {
        for (const e of d.events) this.where.set(e.id, ref.key);
        this.loaded.set(ref.key, d.events);
        return d.events;
      });
      p.catch(() => this.shards.delete(ref.key));
      this.shards.set(ref.key, p);
    }
    return p;
  }

  private static wanted(m: CityManifest, need: Need): ShardRef[] {
    return m.shards.filter((s) => {
      if (s.kind === "past") return !!need.past;
      if (need.all) return true;
      if (s.kind === "ongoing" || s.kind === "deadlines") return true;
      if (s.kind === "openings") return !!need.openings;
      if (s.kind === "week") return Date.parse(`${s.starts}T00:00:00Z`) < need.until;
      return false; // later: only for "everything"
    });
  }

  private merged(meta: CityFeed): CityFeed {
    const events = ([] as Event[]).concat(...this.loaded.values()).sort(byStart);
    return { ...meta, events };
  }

  /** Every upcoming shard is in (the past weeks load only when a view asks for them). */
  private complete(m: CityManifest): boolean {
    return m.shards.every((s) => s.kind === "past" || this.loaded.has(s.key));
  }

  /** The merged feed once the metadata and every shard `need` asks for are in. */
  async ensure(need: Need): Promise<CityFeed> {
    const m = await this.manifest;
    if (!m) return (this.legacy ??= getJSON<CityFeed>(`cities/${this.slug}.json`));
    this.meta ??= this.file(m.meta.file) as Promise<CityFeed>;
    try {
      const [meta] = await Promise.all([this.meta, ...CityData.wanted(m, need).map((s) => this.shard(s))]);
      return this.merged(meta);
    } catch (e) {
      if (this.restart(e)) return this.ensure(need);
      throw e;
    }
  }

  /** What `need` asks for first, then each remaining upcoming shard in idle time (soonest first). */
  async all(need: Need = priority(new Date())): Promise<CityFeed> {
    const first = await this.ensure(need);
    const m = await this.manifest;
    if (!m) {
      this.emit(first, true);
      return first;
    }
    const rest = m.shards.filter((s) => !this.loaded.has(s.key) && (s.kind !== "past" || need.past));
    for (const s of rest) {
      await new Promise<void>((ok) => idle(ok));
      try {
        await this.shard(s);
      } catch (e) {
        if (this.restart(e)) return this.all(need);
        throw e;
      }
    }
    const meta = await this.meta!;
    const f = this.merged(meta);
    this.emit(f, this.complete(m));
    return f;
  }

  /** Start loading everything in the background unless the visitor asked to save data. */
  prefetch(onDone: (f: CityFeed, complete: boolean) => void, need?: Need): void {
    this.listeners.add(onDone);
    if (this.idleStarted || saveData()) return;
    this.idleStarted = true;
    this.all(need).catch(() => {
      this.idleStarted = false; // a later navigation retries
    });
  }

  off(fn: (f: CityFeed, complete: boolean) => void): void {
    this.listeners.delete(fn);
  }

  private emit(f: CityFeed, complete: boolean): void {
    for (const fn of this.listeners) fn(f, complete);
  }

  /** Provenance + the full description for one event: its shard's details file, else the legacy details file. */
  async detail(id: string): Promise<EventDetail | null> {
    const m = await this.manifest.catch(() => null);
    const key = this.where.get(id);
    const ref = m && key ? m.shards.find((s) => s.key === key) : undefined;
    if (ref) {
      const d = (await this.file(ref.details.file)) as CityShardDetailsDoc;
      return d.events[id] ?? null;
    }
    const d = await getJSON<CityDetails>(`cities/${this.slug}.details.json`);
    return d.events[id] ?? null;
  }
}

/** The current and next week (plus ongoing things and upcoming deadlines): what to load before rendering. */
export function priority(now: Date): Need {
  return { until: now.getTime() + 8 * DAY };
}

/** What a page needs before it's correct: the date window of its filter, or everything for whole-feed views. */
export function needFor(view: string, when: string, eventId: string | null, now: Date): Need {
  if (eventId || view === "saved") return { until: Infinity, all: true, past: true };
  if (view === "calendar" || view === "plan") return { until: Infinity, all: true };
  if (view === "deadlines") return priority(now);
  const t = now.getTime();
  switch (when) {
    case "today":
    case "tomorrow":
    case "weekend":
      return { until: t + 8 * DAY };
    case "week":
      return { until: t + 8 * DAY, openings: true };
    case "month":
      return { until: t + 31 * DAY, openings: true };
    default:
      return { until: Infinity, all: true };
  }
}

const cities = new Map<string, CityData>();

export function city(slug: string): CityData {
  let c = cities.get(slug);
  if (!c) {
    c = new CityData(slug);
    cities.set(slug, c);
  }
  return c;
}

/** The whole city feed (every shard, or the legacy file). */
export const loadCity = (slug: string) => city(slug).all({ until: Infinity, all: true, past: true });

const detailCache = new Map<string, Promise<EventDetail | null>>();

/** Provenance + full description for one event, fetched the first time its card is opened. */
export function loadDetail(slug: string, id: string): Promise<EventDetail | null> {
  const k = `${slug}:${id}`;
  let p = detailCache.get(k);
  if (!p) {
    p = city(slug).detail(id);
    p.catch(() => detailCache.delete(k));
    detailCache.set(k, p);
  }
  return p;
}
