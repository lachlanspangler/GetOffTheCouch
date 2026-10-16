// `npm run eval:rank`: offline ranking evaluation (RANKING.md §3.2). Frozen real snapshots × personas ×
// hand-made judgments → NDCG@10, P@10, ILD, family entropy, coverage, freshness, staleness, junk, judged@10.
// Prints a v1-vs-v2 table and fails when v2 misses a gate in fixtures/baseline.json.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { Scored } from "../../src/lib/rank/index";
import {
  CITIES,
  coverage,
  FIX,
  highlights2,
  highlightsV1,
  judgments,
  mean,
  metrics,
  PERSONAS,
  persona,
  poolV2,
  runV1,
  runV2,
  snapshot,
  type Metrics,
} from "./evalLib";

interface Gates {
  ndcg_drop: number; // allowed drop vs the stored v2 numbers
  p10_drop: number;
  ild: number;
  entropy: number;
  coverage: number;
  fresh_h: number;
  stale: number;
  junk_newcomer: number; // grade-0 share for the no-profile persona (for personas a 0 often means "not my thing")
  judged: number;
  highlights_vs_v1: number; // Highlights NDCG@6 may not fall below v1 by more than this
}

interface Baseline {
  gates: Gates;
  v2: { ndcg: number; p10: number };
}

const baseline = JSON.parse(readFileSync(join(FIX, "baseline.json"), "utf8")) as Baseline;

type Row = { city: string; persona: string; v1: Metrics; v2: Metrics };

function evaluate() {
  const rows: Row[] = [];
  const cov: { city: string; v1: number; v2: number }[] = [];
  const hl: { city: string; v1: Metrics; v2: Metrics }[] = [];
  for (const city of CITIES) {
    const s = snapshot(city);
    const j = judgments(city);
    const now = new Date(s.now);
    const pool = poolV2(s, null).map((x) => x.event);
    const l1: Scored[][] = [];
    const l2: Scored[][] = [];
    for (const pid of PERSONAS) {
      const p = persona(pid, city);
      const a = runV1(s, p);
      const b = runV2(s, p);
      l1.push(a);
      l2.push(b);
      rows.push({ city, persona: pid, v1: metrics(a, j, pid, pool, now), v2: metrics(b, j, pid, pool, now) });
    }
    cov.push({ city, v1: coverage(l1, pool), v2: coverage(l2, pool) });
    hl.push({ city, v1: metrics(highlightsV1(s), j, "newcomer_default", pool, now, 6), v2: metrics(highlights2(s), j, "newcomer_default", pool, now, 6) });
  }
  return { rows, cov, hl };
}

const f2 = (x: number) => x.toFixed(2);
const KEYS: (keyof Metrics)[] = ["ndcg", "ndcgCaps", "p10", "ild", "entropy", "junk", "judged", "stale", "freshH"];

function macro(rows: { v1: Metrics; v2: Metrics }[], k: keyof Metrics, side: "v1" | "v2") {
  return mean(rows.map((r) => r[side][k]));
}

function table(res: ReturnType<typeof evaluate>): string {
  const out: string[] = [];
  out.push(`${"city".padEnd(12)}${"persona".padEnd(18)}${KEYS.map((k) => `${k} v1→v2`.padEnd(17)).join("")}`);
  for (const r of res.rows) {
    out.push(`${r.city.padEnd(12)}${r.persona.padEnd(18)}${KEYS.map((k) => `${f2(r.v1[k])}→${f2(r.v2[k])}`.padEnd(17)).join("")}`);
  }
  out.push("");
  out.push(`${"MACRO".padEnd(30)}${KEYS.map((k) => `${f2(macro(res.rows, k, "v1"))}→${f2(macro(res.rows, k, "v2"))}`.padEnd(17)).join("")}`);
  const nc = res.rows.filter((r) => r.persona === "newcomer_default");
  out.push(`v2 macro (for baseline.json): ndcg ${macro(res.rows, "ndcg", "v2").toFixed(3)} p10 ${macro(res.rows, "p10", "v2").toFixed(3)}`);
  out.push(`newcomer_default junk@10 v1→v2: ${f2(macro(nc, "junk", "v1"))}→${f2(macro(nc, "junk", "v2"))}`);
  out.push(`coverage v1→v2: ${res.cov.map((c) => `${c.city} ${f2(c.v1)}→${f2(c.v2)}`).join(" · ")}`);
  out.push(`highlights@6 (newcomer) NDCG v1→v2: ${res.hl.map((h) => `${h.city} ${f2(h.v1.ndcg)}→${f2(h.v2.ndcg)}`).join(" · ")}`);
  out.push(`highlights@6 junk v1→v2: ${res.hl.map((h) => `${h.city} ${f2(h.v1.junk)}→${f2(h.v2.junk)}`).join(" · ")}`);
  return out.join("\n");
}

describe("offline ranking eval (RANKING.md §3.2)", () => {
  const res = evaluate();
  const g = baseline.gates;
  const newcomer = res.rows.filter((r) => r.persona === "newcomer_default");
  it("prints the v1 vs v2 table", () => {
    console.log("\n" + table(res) + "\n");
  });
  it("judged@10 is high enough to trust the numbers (else: relabel, not 'quality dropped')", () => {
    expect(macro(res.rows, "judged", "v2")).toBeGreaterThanOrEqual(g.judged);
    expect(macro(res.rows, "judged", "v1")).toBeGreaterThanOrEqual(g.judged);
  });
  it("v2 relevance doesn't regress against its stored numbers", () => {
    expect(macro(res.rows, "ndcg", "v2")).toBeGreaterThanOrEqual(baseline.v2.ndcg - g.ndcg_drop);
    expect(macro(res.rows, "p10", "v2")).toBeGreaterThanOrEqual(baseline.v2.p10 - g.p10_drop);
  });
  it("Highlights (the cold-start front page) are at least as relevant as v1", () => {
    expect(mean(res.hl.map((h) => h.v2.ndcg))).toBeGreaterThanOrEqual(mean(res.hl.map((h) => h.v1.ndcg)) - g.highlights_vs_v1);
    expect(mean(res.hl.map((h) => h.v2.junk))).toBeLessThanOrEqual(g.junk_newcomer);
  });
  it("v2 meets the beyond-accuracy gates", () => {
    expect(macro(res.rows, "ild", "v2")).toBeGreaterThanOrEqual(g.ild);
    expect(macro(res.rows, "entropy", "v2")).toBeGreaterThanOrEqual(g.entropy);
    expect(mean(res.cov.map((c) => c.v2))).toBeGreaterThanOrEqual(g.coverage);
    expect(macro(res.rows, "freshH", "v2")).toBeLessThanOrEqual(g.fresh_h);
    expect(macro(res.rows, "stale", "v2")).toBeLessThanOrEqual(g.stale);
    expect(macro(newcomer, "junk", "v2")).toBeLessThanOrEqual(g.junk_newcomer);
  });
});
