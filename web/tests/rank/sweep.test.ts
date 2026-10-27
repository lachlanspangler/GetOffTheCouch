// Dev aid, skipped unless GOTC_SWEEP=1: MMR λ sweep with leave-one-city-out selection (RANKING.md §1D:
// "weights must not raise NDCG in one city by tanking another"). Prints per-city NDCG/ILD per λ and the
// held-out NDCG when each city's λ is chosen on the other cities only.
import { describe, it } from "vitest";
import type { Event } from "../../src/lib/types";
import { capKey, orgOf, venueOf, type Caps } from "../../src/lib/rank/diversify";
import { highlightsV2 } from "../../src/lib/rank/index";
import { CITIES, ctxFor, judgments, mean, metrics, PERSONAS, persona, poolV2, runV2, snapshot } from "./evalLib";

const LAMBDAS = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1];

describe.skipIf(!process.env.GOTC_SWEEP)("λ sweep", () => {
  it("prints", () => {
    const ndcg: Record<string, Record<number, number>> = {};
    const ild: Record<number, number[]> = {};
    for (const city of CITIES) {
      const s = snapshot(city);
      const j = judgments(city);
      const pool = poolV2(s, null).map((x) => x.event);
      ndcg[city] = {};
      for (const lam of LAMBDAS) {
        const ms = PERSONAS.map((pid) => metrics(runV2(s, persona(pid, city), 10, { lambda: lam }), j, pid, pool, new Date(s.now)));
        ndcg[city][lam] = mean(ms.map((m) => m.ndcg));
        (ild[lam] ??= []).push(...ms.map((m) => m.ild));
      }
    }
    const lines = LAMBDAS.map((l) => `λ=${l.toFixed(2)} ${CITIES.map((c) => `${c} ${ndcg[c][l].toFixed(3)}`).join(" ")} | mean ${mean(CITIES.map((c) => ndcg[c][l])).toFixed(3)} ILD ${mean(ild[l]).toFixed(3)}`);
    const held = CITIES.map((c) => {
      const others = CITIES.filter((x) => x !== c);
      const best = LAMBDAS.reduce((a, b) => (mean(others.map((o) => ndcg[o][b])) > mean(others.map((o) => ndcg[o][a])) ? b : a));
      return `${c}: λ*=${best} held-out ${ndcg[c][best].toFixed(3)}`;
    });
    console.log("\n" + lines.join("\n") + "\nLOCO: " + held.join(" · "));
  });
});

// I-160 cap sweep (RANKING.md §7.7): cap key × per-key cap × per-source backstop × soft per-family cap, For You
// and Highlights. The key (organizer × venue) is fixed by design, not by this sweep; the alternative keys are
// printed in-sample for comparison only. Leave-one-city-out over the org×venue grid: each fold picks the config
// with the best mean NDCG on the other 4 cities among configs that pass the ILD / entropy / no-profile junk gates
// there (ties within 0.002 go to the stricter, earlier config), then reports its NDCG on the held-out city.
const src = (e: Event) => `src:${e.sources[0]?.source_id ?? ""}`;
const KEYS: Record<string, (e: Event) => string> = {
  "org×venue": capKey,
  "org|venue": (e) => orgOf(e) || venueOf(e) || src(e),
  "venue|org": (e) => venueOf(e) || orgOf(e) || src(e),
};
interface Cfg {
  name: string;
  caps: Partial<Caps>;
  tunable: boolean;
}
const OLD: Cfg = { name: "source ≤2 (old)", caps: { maxPerSource: 2, maxPerKey: undefined, maxPerFamily: undefined }, tunable: true };
const CONFIGS: Cfg[] = [OLD];
for (const perFamily of [undefined, 3, 4, 5])
  for (const [kn, key] of Object.entries(KEYS))
    for (const perKey of [1, 2])
      for (const perSource of [2, 3, 4, 5, 10])
        if (perSource > perKey)
          CONFIGS.push({
            name: `${kn} ≤${perKey}, src ≤${perSource}${perFamily ? `, fam ≤${perFamily}` : ""}`,
            caps: { key, maxPerKey: perKey, maxPerSource: perSource, maxPerFamily: perFamily },
            tunable: key === capKey,
          });

describe.skipIf(!process.env.GOTC_SWEEP)("I-160 cap sweep", () => {
  it("prints For You", { timeout: 600_000 }, () => {
    type M = { ndcg: number; ild: number; entropy: number; junkNc: number };
    const res: Record<string, Record<string, M>> = {};
    for (const city of CITIES) {
      const s = snapshot(city);
      const j = judgments(city);
      const pool = poolV2(s, null).map((x) => x.event);
      for (const c of CONFIGS) {
        const ms = PERSONAS.map((pid) => ({ pid, m: metrics(runV2(s, persona(pid, city), 10, { caps: c.caps }), j, pid, pool, new Date(s.now)) }));
        (res[c.name] ??= {})[city] = {
          ndcg: mean(ms.map((x) => x.m.ndcg)),
          ild: mean(ms.map((x) => x.m.ild)),
          entropy: mean(ms.map((x) => x.m.entropy)),
          junkNc: ms.find((x) => x.pid === "newcomer_default")!.m.junk,
        };
      }
    }
    const agg = (name: string, cities: string[], k: keyof M) => mean(cities.map((c) => res[name][c][k]));
    const ok = (name: string, cities: string[]) => agg(name, cities, "ild") >= 0.55 && agg(name, cities, "entropy") >= 0.7 && agg(name, cities, "junkNc") <= 0.1;
    const worst = (name: string) => Math.min(...CITIES.map((x) => res[name][x].ndcg - res[OLD.name][x].ndcg));
    const lines = CONFIGS.map(
      (c) =>
        `${c.name.padEnd(30)} ${CITIES.map((x) => `${x.slice(0, 4)} ${res[c.name][x].ndcg.toFixed(3)}`).join(" ")} | ndcg ${agg(c.name, CITIES, "ndcg").toFixed(3)} ild ${agg(c.name, CITIES, "ild").toFixed(3)} H ${agg(c.name, CITIES, "entropy").toFixed(3)} junkNc ${agg(c.name, CITIES, "junkNc").toFixed(3)} worst-city Δ ${worst(c.name).toFixed(3)}${ok(c.name, CITIES) ? "" : " ✗gate"}`,
    );
    const held = CITIES.map((c) => {
      const train = CITIES.filter((x) => x !== c);
      let best: Cfg = OLD;
      for (const cfg of CONFIGS) if (cfg.tunable && ok(cfg.name, train) && agg(cfg.name, train, "ndcg") > agg(best.name, train, "ndcg") + 0.002) best = cfg;
      return { c, best: best.name, train: agg(best.name, train, "ndcg"), test: res[best.name][c].ndcg, old: res[OLD.name][c].ndcg };
    });
    const loco = held.map((h) => `  ${h.c.padEnd(12)} pick "${h.best}"  in-sample ${h.train.toFixed(3)}  held-out ${h.test.toFixed(3)}  (old cap ${h.old.toFixed(3)})`);
    console.log(`\n${lines.join("\n")}\nLOCO (For You NDCG@10):\n${loco.join("\n")}\n  mean held-out ${mean(held.map((h) => h.test)).toFixed(3)} vs old ${mean(held.map((h) => h.old)).toFixed(3)}`);
  });
  it("prints Highlights", { timeout: 120_000 }, () => {
    const lines: string[] = [];
    for (const perSource of [1, 2, 3])
      for (const perKey of [1, 2]) {
        if (perKey > perSource) continue;
        const nd: number[] = [];
        const junk: number[] = [];
        for (const city of CITIES) {
          const s = snapshot(city);
          const pool = poolV2(s, null).map((x) => x.event);
          const h = highlightsV2(s.events, ctxFor(s, null, { caps: { maxPerKey: perKey, maxPerSource: perSource } }), 6);
          const m = metrics(h, judgments(city), "newcomer_default", pool, new Date(s.now), 6);
          nd.push(m.ndcg);
          junk.push(m.junk);
        }
        lines.push(`highlights key ≤${perKey} source ≤${perSource}: ${CITIES.map((c, i) => `${c.slice(0, 4)} ${nd[i].toFixed(2)}`).join(" ")} | mean ${mean(nd).toFixed(3)} junk ${mean(junk).toFixed(3)}`);
      }
    console.log("\n" + lines.join("\n"));
  });
});
