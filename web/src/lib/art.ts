// Deterministic, theme-agnostic SVG art (DESIGN.md §6). Same id → same picture, forever.
//
// Safety: the SVG contains only numbers and constant strings. No event text ever enters it, so
// rendering it with dangerouslySetInnerHTML is XSS-safe by construction (asserted in tests/art.test.ts).
// Colors: only the four T.* tones (CSS vars resolved by the `.art` wrapper in app.css) plus "none".

export type Family =
  | "music"
  | "nightlife"
  | "volunteer"
  | "food_drink"
  | "community"
  | "arts"
  | "family"
  | "outdoors"
  | "sports_league"
  | "fitness"
  | "learning"
  | "trivia_games"
  | "sports_watch"
  | "niche"
  | "other";

export const ART_HUE: Record<Family, number> = {
  music: 295,
  nightlife: 330,
  volunteer: 10,
  food_drink: 45,
  community: 75,
  arts: 95,
  family: 115,
  outdoors: 135,
  sports_league: 155,
  fitness: 175,
  learning: 200,
  trivia_games: 225,
  sports_watch: 250,
  niche: 275,
  other: 70,
};

export const FAMILIES = Object.keys(ART_HUE) as Family[];

/** Top-level family of a taxonomy id ("music.concert" → "music"); unknown → "other". */
export function familyOf(categoryId: string): Family {
  const head = categoryId.split(".")[0];
  return Object.prototype.hasOwnProperty.call(ART_HUE, head) ? (head as Family) : "other";
}

/** FNV-1a 32-bit */
export function hash(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** mulberry32: tiny, fast, good enough for art */
export function rng(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type R = () => number;
const pick = <T>(r: R, xs: readonly T[]): T => xs[Math.floor(r() * xs.length)];
const between = (r: R, lo: number, hi: number): number => lo + r() * (hi - lo);
/** Inclusive integer in [lo, hi]. */
const int = (r: R, lo: number, hi: number): number => lo + Math.floor(r() * (hi - lo + 1));
/** 1 decimal keeps strings short. */
const f = (n: number): number => Math.round(n * 10) / 10;

const W = 160,
  H = 100;
export const T = { bg: "var(--art-bg)", mid: "var(--art-mid)", ink: "var(--art-ink)", acc: "var(--art-acc)" } as const;
type Tone = (typeof T)[keyof typeof T];

// ---- tiny element helpers (all numeric input goes through f) ----
const fill = (c: Tone): string => ` fill="${c}"`;
const stroke = (c: Tone, w: number): string => ` fill="none" stroke="${c}" stroke-width="${f(w)}"`;
const g = (attrs: string, body: string): string => (body ? `<g${attrs}>${body}</g>` : "");
const circle = (cx: number, cy: number, rad: number, attrs = ""): string =>
  `<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(rad)}"${attrs}/>`;
const rect = (x: number, y: number, w: number, h: number, rx = 0, attrs = ""): string =>
  `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}"${rx ? ` rx="${f(rx)}"` : ""}${attrs}/>`;
const line = (x1: number, y1: number, x2: number, y2: number, attrs = ""): string =>
  `<line x1="${f(x1)}" y1="${f(y1)}" x2="${f(x2)}" y2="${f(y2)}"${attrs}/>`;
const path = (d: string, attrs = ""): string => `<path d="${d}"${attrs}/>`;
/** "M x y L x y …" from points (numbers rounded). */
const poly = (pts: ReadonlyArray<readonly [number, number]>, close = false): string =>
  pts.map(([x, y], i) => `${i ? "L" : "M"}${f(x)} ${f(y)}`).join("") + (close ? "Z" : "");

type Box = { x: number; y: number; w: number; h: number };
const overlaps = (a: Box, b: Box, m: number): boolean =>
  a.x < b.x + b.w + m && b.x < a.x + a.w + m && a.y < b.y + b.h + m && b.y < a.y + a.h + m;

type Motif = (r: R) => string;

const MOTIFS: Record<Family, Motif> = {
  /** Grooves: 6–10 concentric arcs from a corner, alternating stroke widths. */
  music: (r) => {
    const [c0x, c0y] = pick(r, [[0, 0], [W, 0], [0, H], [W, H]] as const);
    const cx = c0x + between(r, -15, 15),
      cy = c0y + between(r, -12, 12);
    const n = int(r, 6, 10),
      step = between(r, 13, 19),
      accent = int(r, 1, n);
    const [thin, thick] = pick(r, [[2, 6], [1.5, 5], [3, 8]] as const);
    let s = "";
    for (let i = 1; i <= n; i++)
      s += circle(cx, cy, i * step, stroke(i === accent ? T.acc : i % 2 ? T.ink : T.mid, i % 2 ? thin : thick));
    return s;
  },

  /** Halftone: a dot grid whose radius falls off from a seeded focal point. */
  nightlife: (r) => {
    const fx = between(r, 20, W - 20),
      fy = between(r, 15, H - 15);
    const p = int(r, 18, 22),
      max = between(r, 4, 7);
    let ink = "",
      acc = "";
    for (let x = p / 2; x < W; x += p)
      for (let y = p / 2; y < H; y += p) {
        const d = Math.hypot(x - fx, y - fy) / 110,
          rad = max * (1 - d);
        if (rad <= 0.6) continue;
        if (d < 0.15) acc += circle(x, y, rad);
        else ink += circle(x, y, rad);
      }
    // pitch ≥18 on 160×100 → at most 9×6 = 54 dots (asserted in tests)
    return g(fill(T.ink), ink) + g(fill(T.acc), acc);
  },

  /** Linked rings: 3–5 overlapping circles in a row or a gentle arc; one is filled. */
  volunteer: (r) => {
    const n = int(r, 3, 5),
      k = between(r, 1.2, 1.6); // centre spacing / radius
    const rad = Math.min(between(r, 15, 26), 146 / ((n - 1) * k + 2));
    const dx = rad * k,
      x0 = W / 2 - ((n - 1) * dx) / 2 + between(r, -4, 4);
    const base = between(r, 40, 62),
      arc = r() < 0.5 ? 0 : between(r, 6, 16);
    const filled = Math.floor(r() * n);
    const pts = Array.from({ length: n }, (_, i) => {
      const t = (2 * i) / (n - 1) - 1;
      return [x0 + i * dx, base - arc * (1 - t * t)] as const;
    });
    const [fx, fy] = pts[filled];
    return circle(fx, fy, rad, fill(T.acc)) + g(stroke(T.ink, between(r, 2.5, 4)), pts.map(([x, y]) => circle(x, y, rad)).join(""));
  },

  /** Table: one big plate, 2–4 small circles and one rounded bar (utensil-like, abstract). */
  food_drink: (r) => {
    const pr = between(r, 24, 34),
      px = between(r, 40, W - 40),
      py = between(r, 34, H - 34);
    const bw = between(r, 5, 8),
      bh = between(r, 48, 72);
    const left = px > W / 2 ? r() < 0.75 : r() < 0.25;
    const bx = left ? px - pr - between(r, 8, 16) - bw : px + pr + between(r, 8, 16);
    const bar: Box = { x: bx, y: py - bh / 2, w: bw, h: bh };
    const want = int(r, 2, 4);
    const dots: Array<[number, number, number]> = [];
    for (let tries = 0; tries < 40 && dots.length < want; tries++) {
      const sr = between(r, 5, 11),
        x = between(r, sr + 4, W - sr - 4),
        y = between(r, sr + 4, H - sr - 4);
      const b: Box = { x: x - sr, y: y - sr, w: 2 * sr, h: 2 * sr };
      if (Math.hypot(x - px, y - py) < pr + sr + 5 || overlaps(b, bar, 4)) continue;
      if (dots.some(([ox, oy, or]) => Math.hypot(x - ox, y - oy) < sr + or + 4)) continue;
      dots.push([x, y, sr]);
    }
    return (
      circle(px, py, pr, fill(T.mid)) +
      circle(px, py, pr * between(r, 0.6, 0.75), stroke(T.ink, 1.5)) +
      rect(bar.x, bar.y, bar.w, bar.h, bw / 2, fill(T.ink)) +
      dots.map(([x, y, sr], i) => circle(x, y, sr, fill(i === 0 ? T.acc : i % 2 ? T.ink : T.mid))).join("")
    );
  },

  /** Quilt: a 4×6 grid, each cell blank, a half-diagonal or a quarter-circle. */
  community: (r) => {
    const cols = 6,
      rows = 4,
      cw = W / cols,
      ch = H / rows,
      R = Math.min(cw, ch);
    const accA = Math.floor(r() * cols * rows),
      accB = Math.floor(r() * cols * rows);
    const out: Record<"ink" | "mid" | "acc", string> = { ink: "", mid: "", acc: "" };
    for (let i = 0; i < cols * rows; i++) {
      const x = (i % cols) * cw,
        y = Math.floor(i / cols) * ch;
      const kind = r(),
        k = Math.floor(r() * 4),
        tone = i === accA || i === accB ? "acc" : r() < 0.55 ? "ink" : "mid";
      if (kind < 0.22) continue; // blank
      // corners clockwise from top-left
      const corners = [[x, y], [x + cw, y], [x + cw, y + ch], [x, y + ch]] as const;
      if (kind < 0.62) {
        out[tone] += path(poly(corners.filter((_, j) => j !== k), true));
      } else {
        const [cx, cy] = corners[k];
        const dx = k === 0 || k === 3 ? 1 : -1,
          dy = k < 2 ? 1 : -1;
        const sweep = dx * dy > 0 ? 1 : 0;
        out[tone] += path(`M${f(cx)} ${f(cy)}L${f(cx + dx * R)} ${f(cy)}A${f(R)} ${f(R)} 0 0 ${sweep} ${f(cx)} ${f(cy + dy * R)}Z`);
      }
    }
    return g(fill(T.mid), out.mid) + g(fill(T.ink), out.ink) + g(fill(T.acc), out.acc);
  },

  /** Arches: 3–5 nested semicircles (rainbow arch) on a ground line. */
  arts: (r) => {
    const gy = between(r, 70, 88),
      n = int(r, 3, 5),
      cx = between(r, 45, W - 45);
    const Rmax = between(r, 44, Math.min(70, gy - 4));
    const t = (between(r, 0.7, 1) * Rmax) / (n + 1);
    const accI = Math.floor(r() * n),
      startInk = r() < 0.5;
    const arch = (R: number, c: Tone): string =>
      path(`M${f(cx - R)} ${f(gy)}A${f(R)} ${f(R)} 0 0 1 ${f(cx + R)} ${f(gy)}Z`, fill(c));
    let s = rect(0, gy, W, H - gy, 0, fill(T.mid));
    for (let i = 0; i < n; i++) s += arch(Rmax - i * t, i === accI ? T.acc : (i % 2 === 0) === startInk ? T.ink : T.mid);
    s += arch(Rmax - n * t, T.bg);
    return s + rect(0, gy - 0.75, W, 1.5, 0, fill(T.ink));
  },

  /** Pebbles: 5–8 pill-shaped rounded rects scattered without overlap (rejection sampling). */
  family: (r) => {
    const want = int(r, 5, 8),
      accI = Math.floor(r() * want);
    const placed: Box[] = [];
    let s = "";
    for (let i = 0; i < want; i++) {
      for (let tries = 0; tries < 40; tries++) {
        const h = between(r, 10, 22),
          w = between(r, h * 1.4, h * 3.2);
        const b: Box = { x: between(r, 4, W - 4 - w), y: between(r, 4, H - 4 - h), w, h };
        if (placed.some((p) => overlaps(b, p, 4))) continue;
        placed.push(b);
        s += rect(b.x, b.y, b.w, b.h, h / 2, fill(i === accI ? T.acc : i % 2 ? T.ink : T.mid));
        break;
      }
    }
    return s;
  },

  /** Contours: 6–9 stacked smooth sine paths (topographic). */
  outdoors: (r) => {
    const n = 6 + Math.floor(r() * 4),
      amp = between(r, 4, 10),
      freq = between(r, 1, 2.2),
      ph = r() * Math.PI * 2;
    const accI = int(r, 1, n - 2);
    let s = "";
    for (let i = 0; i < n; i++) {
      const y0 = (H / (n + 1)) * (i + 1);
      let d = `M0 ${f(y0 + amp * Math.sin(ph + i * 0.35))}`;
      for (let x = 8; x <= W; x += 8) d += `L${x} ${f(y0 + amp * Math.sin((x / W) * freq * Math.PI * 2 + ph + i * 0.35))}`;
      s += path(d, i === accI ? ` stroke="${T.acc}"` : "");
    }
    return g(`${stroke(T.ink, 1.5)} stroke-linejoin="round"`, s);
  },

  /** Field: mowed-grass stripes plus a centre circle and halfway line in ink at 1.5px. */
  sports_league: (r) => {
    const k = int(r, 5, 8),
      vertical = r() < 0.5,
      cr = between(r, 12, 24),
      inset = between(r, 6, 12);
    let bands = "";
    for (let i = 1; i < k; i += 2)
      bands += vertical ? rect((W / k) * i, 0, W / k, H) : rect(0, (H / k) * i, W, H / k);
    const lines =
      rect(inset, inset, W - 2 * inset, H - 2 * inset) +
      line(W / 2, inset, W / 2, H - inset) +
      circle(W / 2, H / 2, cr) +
      rect(inset, H / 2 - cr, cr * 0.9, 2 * cr) +
      rect(W - inset - cr * 0.9, H / 2 - cr, cr * 0.9, 2 * cr);
    return g(fill(T.mid), bands) + g(stroke(T.ink, 1.5), lines) + circle(W / 2, H / 2, 2.5, fill(T.acc));
  },

  /** Pace: 8–14 parallel diagonal bars of varying length. */
  fitness: (r) => {
    const a = (between(r, 20, 40) * Math.PI) / 180,
      n = int(r, 8, 14),
      sw = between(r, 3, 6);
    const ux = Math.cos(a),
      uy = -Math.sin(a),
      gap = (W + 40) / n,
      accI = Math.floor(r() * n);
    let ink = "",
      acc = "";
    for (let i = 0; i < n; i++) {
      const x = -20 + i * gap + between(r, 0, gap * 0.4),
        y = H - between(r, 4, 34),
        len = between(r, 22, 80);
      const l = line(x, y, x + ux * len, y + uy * len);
      if (i === accI) acc += l;
      else ink += l;
    }
    return g(`${stroke(T.ink, sw)} stroke-linecap="round"`, ink) + g(`${stroke(T.acc, sw)} stroke-linecap="round"`, acc);
  },

  /** Ruled: horizontal rules every 10px, one vertical margin rule in acc, 0–2 underline marks. */
  learning: (r) => {
    const off = between(r, 3, 10),
      mx = between(r, 18, 44);
    const ys: number[] = [];
    for (let y = off; y < H; y += 10) ys.push(y);
    const rules = ys.map((y) => line(0, y, W, y)).join("");
    let marks = "";
    for (let i = 0, m = int(r, 0, 2); i < m; i++) {
      const y = pick(r, ys),
        x = between(r, mx + 8, W - 60);
      marks += line(x, y - 1.5, x + between(r, 20, 56), y - 1.5);
    }
    return (
      g(stroke(T.mid, 1), rules) +
      line(mx, 0, mx, H, stroke(T.acc, 1.5)) +
      g(`${stroke(T.ink, 3)} stroke-linecap="round"`, marks)
    );
  },

  /** Tiles: a 5×8 grid of rounded squares, 3–5 "flipped" to acc. */
  trivia_games: (r) => {
    const flipped = new Set<number>();
    for (let k = int(r, 3, 5); flipped.size < k; ) flipped.add(Math.floor(r() * 40));
    let mid = "",
      acc = "";
    for (let i = 0; i < 40; i++) {
      const t = rect((i % 8) * 20 + 2, Math.floor(i / 8) * 20 + 2, 16, 16, 3);
      if (flipped.has(i)) acc += t;
      else mid += t;
    }
    return g(fill(T.mid), mid) + g(fill(T.acc), acc);
  },

  /** Pennants: 3–6 triangles or swallowtails hanging from a sagging string. */
  sports_watch: (r) => {
    const n = int(r, 3, 6),
      y0 = between(r, 12, 30),
      sag = between(r, 4, 14);
    const slot = (W - 20) / n,
      tw = slot * between(r, 0.7, 0.92),
      th = between(r, 26, 50);
    const swallow = r() < 0.5,
      accI = Math.floor(r() * n),
      startInk = r() < 0.5;
    const yAt = (x: number): number => y0 + sag * (1 - ((x - W / 2) / (W / 2)) ** 2);
    let s = path(`M0 ${f(y0)}Q${W / 2} ${f(y0 + 2 * sag)} ${W} ${f(y0)}`, stroke(T.ink, 1.5));
    for (let i = 0; i < n; i++) {
      const cx = 10 + (i + 0.5) * slot,
        xl = cx - tw / 2,
        xr = cx + tw / 2;
      const yl = yAt(xl),
        yr = yAt(xr);
      const pts: Array<readonly [number, number]> = swallow
        ? [[xl, yl], [xr, yr], [xr, yr + th], [cx, yAt(cx) + th * 0.7], [xl, yl + th]]
        : [[xl, yl], [xr, yr], [cx, yAt(cx) + th]];
      s += path(poly(pts, true), fill(i === accI ? T.acc : (i % 2 === 0) === startInk ? T.ink : T.mid));
    }
    return s;
  },

  /** Constellation: 6–10 four-point stars joined by 1px lines, over a little star dust. */
  niche: (r) => {
    const want = int(r, 6, 10);
    const pts: Array<[number, number]> = [];
    for (let tries = 0; tries < 40 * want && pts.length < want; tries++) {
      const x = between(r, 10, W - 10),
        y = between(r, 10, H - 10);
      if (pts.every(([px, py]) => Math.hypot(x - px, y - py) >= 20)) pts.push([x, y]);
    }
    pts.sort((a, b) => a[0] - b[0]);
    const accI = Math.floor(r() * pts.length);
    const star = (x: number, y: number, s: number): string => {
      const X = f(x),
        Y = f(y),
        q = `Q${X} ${Y} `;
      return path(`M${X} ${f(y - s)}${q}${f(x + s)} ${Y}${q}${X} ${f(y + s)}${q}${f(x - s)} ${Y}${q}${X} ${f(y - s)}Z`);
    };
    let dust = "";
    for (let i = 0, m = int(r, 8, 14); i < m; i++) dust += circle(between(r, 2, W - 2), between(r, 2, H - 2), 0.8);
    let ink = "",
      acc = "";
    pts.forEach(([x, y], i) => {
      if (i === accI) acc += star(x, y, between(r, 8, 11));
      else ink += star(x, y, between(r, 3.5, 7));
    });
    return (
      g(fill(T.mid), dust) +
      path(poly(pts), stroke(T.ink, 1)) +
      g(fill(T.ink), ink) +
      g(fill(T.acc), acc)
    );
  },

  /** Stone field: 3 overlapping rectangles (no venue initial: a glyph would read as text). */
  other: (r) => {
    const tones = [T.mid, T.ink, T.acc] as const;
    let s = "";
    tones.forEach((tone, i) => {
      const w = between(r, 40, 90) * (i === 2 ? 0.6 : 1),
        h = between(r, 30, 64) * (i === 2 ? 0.6 : 1);
      s += rect(between(r, -10, W - w + 10), between(r, -6, H - h + 6), w, h, 2, fill(tone));
    });
    return s;
  },
};

/** City tiles (home): an abstract street grid of 6–10 blocks, 2 "park" blocks in acc, one avenue. */
function cityBlocks(r: R): string {
  const [cols, rows] = pick(r, [[3, 2], [4, 2], [3, 3], [5, 2]] as const);
  const gap = between(r, 4, 7);
  const split = (n: number, span: number): Array<[number, number]> => {
    const ws = Array.from({ length: n }, () => between(r, 0.6, 1.4));
    const sum = ws.reduce((a, b) => a + b, 0),
      free = span + 12 - (n - 1) * gap;
    let at = -6;
    return ws.map((w) => {
      const seg: [number, number] = [at, (w / sum) * free];
      at += seg[1] + gap;
      return seg;
    });
  };
  const xs = split(cols, W),
    ys = split(rows, H),
    total = cols * rows;
  const parkA = Math.floor(r() * total);
  let parkB = Math.floor(r() * (total - 1));
  if (parkB >= parkA) parkB++;
  let mid = "",
    acc = "";
  for (let i = 0; i < total; i++) {
    const [x, w] = xs[i % cols],
      [y, h] = ys[Math.floor(i / cols)];
    const b = rect(x, y, w, h, 2);
    if (i === parkA || i === parkB) acc += b;
    else mid += b;
  }
  const avenue = line(between(r, 0, W), -5, between(r, 0, W), H + 5, stroke(T.bg, gap));
  return g(fill(T.mid), mid) + g(fill(T.acc), acc) + avenue;
}

export interface ArtOptions {
  id: string;
  family: Family;
  /** Accepted for call-site convenience; never rendered (no event text enters the SVG). */
  title?: string;
}
export interface ArtResult {
  svg: string;
  hue: number;
  shift: number;
}

const cache = new Map<string, string>();
const CACHE_MAX = 512;

function wrap(body: string, rot: number): string {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" focusable="false">` +
    `<rect width="${W}" height="${H}" fill="${T.bg}"/><g transform="rotate(${rot} ${W / 2} ${H / 2})">${body}</g></svg>`
  );
}

function render(key: string, motif: Motif): { svg: string; shift: number } {
  const r = rng(hash(key));
  const shift = pick(r, [-20, 0, 20] as const);
  let svg = cache.get(key);
  if (!svg) {
    const rot = pick(r, [0, 180] as const); // only 0/180 so 16:10 tiles never letterbox
    svg = wrap(motif(r), rot);
    if (cache.size >= CACHE_MAX) cache.clear();
    cache.set(key, svg);
  }
  return { svg, shift };
}

/** Returns an SVG string. Wrap it in <div class="art" data-family=… style="--art-h:…;--art-shift:…" aria-hidden="true">. */
export function artSvg({ id, family }: ArtOptions): ArtResult {
  const fam: Family = Object.prototype.hasOwnProperty.call(MOTIFS, family) ? family : "other";
  const { svg, shift } = render(`${fam}:${id}`, MOTIFS[fam]);
  return { svg, hue: ART_HUE[fam], shift };
}

const CITY_HUES = FAMILIES.filter((x) => x !== "other").map((x) => ART_HUE[x]);

/** Home-page city tile art, seeded by city slug (hue is seeded too, from the family hue wheel). */
export function cityArt(slug: string): ArtResult {
  const key = `city:${slug}`;
  const { svg, shift } = render(key, cityBlocks);
  return { svg, hue: pick(rng(hash(`${key}:hue`)), CITY_HUES), shift };
}
