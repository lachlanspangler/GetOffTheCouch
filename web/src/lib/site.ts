// Where the site lives. Every href, canonical, sitemap entry and share URL goes through here, so moving to a
// custom domain is one env var (GOTC_BASE=/, GOTC_SITE_ORIGIN=https://…) and a rebuild.
import type { Filters, When } from "./filters";

declare const __SITE_ORIGIN__: string | undefined;

/** Always starts and ends with "/" ("/" in dev, "/GetOffTheCouch/" on GitHub Pages). */
export const BASE: string = (() => {
  const b = (import.meta.env?.BASE_URL as string | undefined) ?? "/";
  const s = b.startsWith("/") ? b : `/${b}`;
  return s.endsWith("/") ? s : `${s}/`;
})();

export const ORIGIN: string =
  (typeof __SITE_ORIGIN__ !== "undefined" && __SITE_ORIGIN__) ||
  (typeof location !== "undefined" ? location.origin : "https://lachlanspangler.github.io");

/** "chicago/concerts/" → "/GetOffTheCouch/chicago/concerts/" */
export function url(path = ""): string {
  return BASE + path.replace(/^\//, "");
}

export function absolute(path = ""): string {
  return ORIGIN + url(path);
}

export function slugify(s: string, max = 60): string {
  const out = s
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (out.length <= max) return out;
  const cut = out.slice(0, max);
  return cut.includes("-") ? cut.slice(0, cut.lastIndexOf("-")) : cut;
}

/** Event ids are `evt_<hex>`; the path carries a cosmetic title slug plus the authoritative hex. */
export function eventPath(city: string, id: string, title?: string): string {
  const hex = id.replace(/^evt_/, "");
  const s = title ? slugify(title) : "";
  return `${city}/events/${s ? `${s}-` : ""}${hex}/`;
}

export function idFromEventSegment(seg: string): string | null {
  const m = /(?:^|-)([0-9a-f]{8,})$/.exec(seg);
  return m ? `evt_${m[1]}` : null;
}

/** Landing pages people actually search for: "<city> concerts", "<city> this weekend", "free things to do". */
export interface Hub {
  slug: string;
  label: string; // "Concerts" → page title "Concerts in Chicago"
  cats?: string[];
  when?: When;
  free?: boolean;
}

export const HUBS: Hub[] = [
  { slug: "today", label: "Things to do today", when: "today" },
  { slug: "this-weekend", label: "Things to do this weekend", when: "weekend" },
  { slug: "free", label: "Free things to do", free: true },
  { slug: "concerts", label: "Concerts & live music", cats: ["music"], when: "month" },
  { slug: "beer-leagues", label: "Rec & beer leagues", cats: ["sports_league"], when: "month" },
  { slug: "trivia", label: "Trivia & games", cats: ["trivia_games"], when: "month" },
  { slug: "nightlife", label: "Parties & nightlife", cats: ["nightlife"], when: "month" },
  { slug: "volunteering", label: "Volunteering", cats: ["volunteer"], when: "month" },
  { slug: "festivals", label: "Festivals & community", cats: ["community"], when: "month" },
  { slug: "food-and-drink", label: "Food, drink & openings", cats: ["food_drink"], when: "month" },
  { slug: "arts", label: "Arts, theater & comedy", cats: ["arts"], when: "month" },
  { slug: "fitness", label: "Run clubs & fitness", cats: ["fitness"], when: "month" },
  { slug: "outdoors", label: "Outdoors", cats: ["outdoors"], when: "month" },
  { slug: "games-to-watch", label: "Games to watch", cats: ["sports_watch"], when: "month" },
  { slug: "cons-and-faires", label: "Cons, faires & niche", cats: ["niche"], when: "month" },
  { slug: "classes", label: "Classes & talks", cats: ["learning"], when: "month" },
  { slug: "family", label: "Family & kids", cats: ["family"], when: "month" },
];

export const HUB_BY_SLUG = new Map(HUBS.map((h) => [h.slug, h]));

/** The hub whose preset is exactly these filters (and nothing else), so the URL can be the clean landing path. */
export function hubFor(f: Filters, defaults: Filters): Hub | undefined {
  const extra =
    f.q || f.maxPrice != null || f.social || f.size !== "any" || f.near || f.tags.length || f.radiusKm !== defaults.radiusKm;
  if (extra) return undefined;
  return HUBS.find(
    (h) =>
      (h.when ?? defaults.when) === f.when &&
      !!h.free === f.free &&
      (h.cats ?? []).join(",") === f.cats.join(","),
  );
}
