// Dev aid, skipped unless GOTC_SWEEP=1: MMR λ sweep with leave-one-city-out selection (RANKING.md §1D:
// "weights must not raise NDCG in one city by tanking another"). Prints per-city NDCG/ILD per λ and the
// held-out NDCG when each city's λ is chosen on the other cities only.
import { describe, it } from "vitest";
import { CITIES, judgments, mean, metrics, PERSONAS, persona, poolV2, runV2, snapshot } from "./evalLib";

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
