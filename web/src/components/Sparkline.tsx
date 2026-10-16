import type { PricePoint } from "../lib/types";
import { money } from "../lib/format";

/** Lowest-price history as a tiny SVG line. Shows nothing rather than a misleading single point. */
export function Sparkline({ points }: { points: PricePoint[] }) {
  const pts = points.filter((p) => p.price_min != null).map((p) => ({ t: new Date(p.at).getTime(), v: p.price_min as number }));
  if (pts.length < 2) return <p class="muted small">Price history appears after a few refreshes.</p>;
  const w = 240, h = 56, pad = 4;
  const t0 = pts[0].t, t1 = pts[pts.length - 1].t;
  const lo = Math.min(...pts.map((p) => p.v)), hi = Math.max(...pts.map((p) => p.v));
  const x = (t: number) => pad + ((t - t0) / Math.max(1, t1 - t0)) * (w - 2 * pad);
  const y = (v: number) => h - pad - ((v - lo) / Math.max(1, hi - lo)) * (h - 2 * pad);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  return (
    <figure class="spark">
      <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} role="img" aria-label={`Lowest price from ${money(pts[0].v)} to ${money(last.v)}`}>
        <path d={d} fill="none" stroke="var(--accent)" stroke-width="2" />
        <circle cx={x(last.t)} cy={y(last.v)} r="3" fill="var(--accent)" />
      </svg>
      <figcaption class="muted small">
        Lowest listed price · {money(lo)}–{money(hi)} over {pts.length} checks
      </figcaption>
    </figure>
  );
}
