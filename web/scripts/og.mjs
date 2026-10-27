// Build-time share cards (I-115, SEO_ACCESS §3.4): a 1200×630 PNG per page worth sharing — the home page, each
// city, each hub, and events in the next 14 days — rendered with satori (layout → SVG) and resvg (SVG → PNG) from
// the page's own art motif plus its title, date and city (lib/og.ts). Images are cached by content hash in
// data/og-cache/ (persisted by the refresh workflow), so an hourly build only renders cards whose text changed.
// Writes dist/og/<key>.<hash>.png and dist/og/manifest.json (page key → file) for scripts/prerender.mjs.
//   node scripts/og.mjs        (after `vite build --ssr src/entry-server.tsx`, before scripts/prerender.mjs)
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, utimesSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { availableParallelism } from "node:os";
import { Worker, isMainThread, parentPort, workerData } from "node:worker_threads";

const here = dirname(fileURLToPath(import.meta.url));
const W = 1200;
const H = 630;
const MAX_BYTES = 100 * 1024;
const EVENT_DAYS = Number(process.env.GOTC_OG_DAYS ?? 14);
// the soonest events per city get their own card (SEO_ACCESS §3.4: ~2k event cards keeps the site far from Pages'
// 1 GB); every other event page shares its category hub's card
const EVENTS_PER_CITY = Number(process.env.GOTC_OG_EVENTS_PER_CITY ?? 60);
const COLORS = 128; // palette PNG: flat art + text quantize cleanly, ~25 KB instead of ~60 KB
const KEEP_DAYS = 3; // cached cards nobody used for this long are pruned, so the Actions cache stays bounded

// ---- colors: the art's four tones are oklch() CSS variables on the site; resvg needs plain sRGB ----------------
function oklchHex(L, C, h) {
  const r = (h * Math.PI) / 180;
  const a = C * Math.cos(r);
  const b = C * Math.sin(r);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
  const g = (x) => Math.round(255 * Math.min(1, Math.max(0, x <= 0.0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - 0.055)));
  return `#${lin.map((x) => g(x).toString(16).padStart(2, "0")).join("")}`;
}
// light-theme tones from styles/app.css (.art, [data-family=city], [data-family=other])
function tones(art) {
  const c = { bg: 0.03, mid: 0.07, ink: 0.1, acc: 0.12 };
  if (art.family === "city") Object.assign(c, { bg: 0.02, mid: 0.045, acc: 0.075 });
  if (art.family === "other") Object.assign(c, { bg: 0, mid: 0, ink: 0, acc: 0.02 });
  return {
    bg: oklchHex(0.95, c.bg, art.hue),
    mid: oklchHex(0.84, c.mid, art.hue),
    ink: oklchHex(0.48, c.ink, art.hue),
    acc: oklchHex(0.7, c.acc, art.hue + art.shift),
  };
}
function artDataUri(art) {
  const t = tones(art);
  const svg = art.svg
    .replaceAll("var(--art-bg)", t.bg)
    .replaceAll("var(--art-mid)", t.mid)
    .replaceAll("var(--art-ink)", t.ink)
    .replaceAll("var(--art-acc)", t.acc)
    .replace("<svg ", `<svg width="${W}" height="${H}" `);
  return { uri: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`, ink: t.ink };
}

const clip = (s, n) => (s.length <= n ? s : `${s.slice(0, n - 1).replace(/\s+\S*$/, "")}…`);
const h = (type, style, children) => ({ type, props: { style, children } });

function layout(card) {
  const art = artDataUri(card.art);
  const title = clip(card.title, 90);
  const size = title.length > 60 ? 56 : title.length > 34 ? 66 : 76;
  return h("div", { width: W, height: H, display: "flex", position: "relative", fontFamily: "Inter" }, [
    { type: "img", props: { src: art.uri, width: W, height: H, style: { position: "absolute", left: 0, top: 0 } } },
    h("div", { position: "absolute", left: 56, top: 48, display: "flex", background: "#ffffff", borderRadius: 999, padding: "10px 24px", fontFamily: "Newsreader", fontSize: 30, color: "#1b1b1f" }, "Get Off the Couch"),
    h("div", { position: "absolute", left: 56, right: 56, bottom: 56, display: "flex", flexDirection: "column", background: "rgba(255,255,255,0.94)", borderRadius: 28, padding: "36px 44px" }, [
      h("div", { fontSize: 24, letterSpacing: 1.5, textTransform: "uppercase", color: art.ink, marginBottom: 12 }, clip(card.kicker, 70)),
      h("div", { fontFamily: "Newsreader", fontSize: size, lineHeight: 1.08, color: "#1b1b1f", marginBottom: 16 }, title),
      h("div", { fontSize: 30, color: "#45454d" }, clip(card.date, 80)),
    ]),
  ]);
}

// ---- worker: render cards to PNG --------------------------------------------------------------------------------
async function renderer() {
  const { default: satori } = await import("satori");
  const { Resvg } = await import("@resvg/resvg-js");
  const { default: UPNG } = await import("upng-js");
  const fonts = [
    { name: "Inter", data: readFileSync(join(here, "og/fonts/Inter.ttf")), weight: 400, style: "normal" },
    { name: "Newsreader", data: readFileSync(join(here, "og/fonts/Newsreader.ttf")), weight: 400, style: "normal" },
  ];
  return async (card) => {
    const svg = await satori(layout(card), { width: W, height: H, fonts });
    const img = new Resvg(svg, { fitTo: { mode: "width", value: W }, font: { loadSystemFonts: false } }).render();
    const px = img.pixels;
    return Buffer.from(UPNG.encode([px.buffer.slice(px.byteOffset, px.byteOffset + px.byteLength)], img.width, img.height, COLORS));
  };
}

if (!isMainThread) {
  const render = await renderer();
  parentPort.on("message", async ({ card, out }) => {
    try {
      writeFileSync(out, await render(card));
      parentPort.postMessage({ ok: true, out });
    } catch (e) {
      parentPort.postMessage({ ok: false, out, error: String(e) });
    }
  });
} else if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}

export { layout, renderer };

async function main() {
  const dist = resolve(here, "../dist");
  const dataDir = join(dist, "data");
  const cacheDir = resolve(process.env.GOTC_OG_CACHE ?? join(here, "../../data/og-cache"));
  if (!existsSync(join(dataDir, "index.json"))) {
    console.log("og: no dist/data/index.json (no pipeline export yet); no share cards");
    return;
  }
  const ssr = await import(resolve(here, "../dist-ssr/entry-server.js"));
  const index = JSON.parse(readFileSync(join(dataDir, "index.json"), "utf8"));
  if (index.is_demo) throw new Error("refusing to render share cards for demo data");
  const now = new Date(process.env.GOTC_PRERENDER_NOW ?? index.generated_at);
  const cards = [ssr.homeCard(index, now)];
  for (const c of index.cities) {
    const f = join(dataDir, "cities", `${c.slug}.json`);
    if (!existsSync(f)) continue;
    const feed = JSON.parse(readFileSync(f, "utf8"));
    if (feed.is_demo) continue;
    cards.push(ssr.cityCard(feed, now));
    for (const hub of ssr.HUBS) {
      const card = ssr.hubCard(feed, hub.slug, now);
      if (card) cards.push(card);
    }
    // the events scripts/prerender.mjs gives a page (one per series), starting in the next EVENT_DAYS days
    const until = now.getTime() + EVENT_DAYS * 86_400_000;
    const seen = new Set();
    let own = 0;
    for (const e of [...feed.events].sort((a, b) => a.start.localeCompare(b.start))) {
      if (own >= EVENTS_PER_CITY) break;
      if (e.is_demo || e.kind === "opening") continue; // an opening's date is a license filing, not a date to go
      if (new Date(e.end ?? e.start).getTime() < now.getTime() - 86_400_000 || new Date(e.start).getTime() > until) continue;
      if (e.series_id) {
        if (seen.has(e.series_id)) continue;
        seen.add(e.series_id);
      }
      cards.push(ssr.eventCard(feed, e));
      own += 1;
    }
  }

  const t0 = Date.now();
  mkdirSync(cacheDir, { recursive: true });
  const out = join(dist, "og");
  rmSync(out, { recursive: true, force: true });
  const manifest = {};
  const cachedAt = {};
  const todo = [];
  for (const card of cards) {
    const hash = createHash("sha256").update(JSON.stringify({ t: ssr.OG_TEMPLATE, card })).digest("hex");
    const cached = join(cacheDir, `${hash}.png`);
    manifest[card.key] = `og/${card.key}.${hash.slice(0, 10)}.png`;
    cachedAt[card.key] = cached;
    if (!existsSync(cached)) todo.push({ card, out: cached });
    else utimesSync(cached, new Date(), new Date()); // mark as used (pruning below)
  }

  // render cache misses on a small worker pool (satori + resvg are CPU-bound)
  const n = Math.max(1, Math.min(todo.length, Number(process.env.GOTC_OG_WORKERS ?? Math.min(4, availableParallelism()))));
  let failed = 0;
  if (todo.length) {
    await new Promise((done) => {
      let next = 0;
      let busy = 0;
      const workers = Array.from({ length: n }, () => new Worker(fileURLToPath(import.meta.url)));
      const feed = (w) => {
        if (next >= todo.length) {
          if (busy === 0) {
            workers.forEach((x) => x.terminate());
            done();
          }
          return;
        }
        busy += 1;
        w.postMessage(todo[next++]);
      };
      for (const w of workers) {
        w.on("message", (m) => {
          busy -= 1;
          if (!m.ok) {
            failed += 1;
            console.error(`og: ${m.out}: ${m.error}`);
          }
          feed(w);
        });
        feed(w);
      }
    });
  }

  let bytes = 0;
  let big = 0;
  for (const card of cards) {
    const file = manifest[card.key];
    const src = cachedAt[card.key];
    if (!existsSync(src)) {
      delete manifest[card.key]; // rendering failed: the page simply has no image (counted above)
      continue;
    }
    const size = statSync(src).size;
    if (size > MAX_BYTES) {
      big += 1;
      delete manifest[card.key];
      continue;
    }
    const dest = join(dist, file);
    mkdirSync(dirname(dest), { recursive: true });
    copyFileSync(src, dest);
    bytes += size;
  }
  writeFileSync(join(out, "manifest.json"), JSON.stringify(manifest));
  let pruned = 0;
  for (const f of readdirSync(cacheDir)) {
    const p = join(cacheDir, f);
    if (Date.now() - statSync(p).mtimeMs > KEEP_DAYS * 86_400_000) {
      rmSync(p);
      pruned += 1;
    }
  }
  const report = { cards: cards.length, rendered: todo.length, cached: cards.length - todo.length, failed, over_100kb: big, pruned, mb: +(bytes / 1e6).toFixed(1), seconds: +((Date.now() - t0) / 1000).toFixed(1), workers: todo.length ? n : 0 };
  writeFileSync(join(out, "report.json"), JSON.stringify(report, null, 2));
  console.log(`og: ${report.cards} share cards (${report.rendered} rendered, ${report.cached} from cache, ${failed} failed, ${big} over 100 KB), ${report.mb} MB in ${report.seconds}s`);
}
