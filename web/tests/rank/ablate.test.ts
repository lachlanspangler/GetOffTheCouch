// Dev aid, skipped unless GOTC_ABLATE=1: macro metrics for v2 variants (what costs relevance, what buys diversity).
import { describe, it } from "vitest";
import type { RankContext } from "../../src/lib/rank/index";
import { CITIES, judgments, mean, metrics, PERSONAS, persona, poolV2, runV1, runV2, snapshot } from "./evalLib";

const VARIANTS: Record<string, Partial<RankContext>> = {
  "v2 (shipped)": {},
  "no explore": { explore: false },
  "no floor": { lastShown: undefined },
  "no explore/floor": { explore: false, lastShown: undefined },
  "λ=1 (no MMR)": { explore: false, lastShown: undefined, lambda: 1 },
  "no source cap": { explore: false, lastShown: undefined, caps: { maxPerSource: undefined } },
  "no caps, λ=1": { explore: false, lastShown: undefined, lambda: 1, caps: { maxPerSource: undefined, minFamilies: 0 } },
};

describe.skipIf(!process.env.GOTC_ABLATE)("ablation", () => {
  it("prints", () => {
    const rows: string[] = [];
    const v1: number[] = [];
    for (const city of CITIES) {
      const s = snapshot(city);
      const pool = poolV2(s, null).map((x) => x.event);
      for (const pid of PERSONAS) v1.push(metrics(runV1(s, persona(pid, city)), judgments(city), pid, pool, new Date(s.now)).ndcg);
    }
    rows.push(`v1: ndcg ${mean(v1).toFixed(3)}`);
    for (const [name, extra] of Object.entries(VARIANTS)) {
      const m: { ndcg: number; caps: number; ild: number; junk: number }[] = [];
      for (const city of CITIES) {
        const s = snapshot(city);
        const j = judgments(city);
        const pool = poolV2(s, null).map((x) => x.event);
        for (const pid of PERSONAS) {
          const r = metrics(runV2(s, persona(pid, city), 10, extra), j, pid, pool, new Date(s.now));
          m.push({ ndcg: r.ndcg, caps: r.ndcgCaps, ild: r.ild, junk: r.junk });
        }
      }
      const f = (k: keyof (typeof m)[0]) => mean(m.map((x) => x[k])).toFixed(3);
      rows.push(`${name.padEnd(20)} ndcg ${f("ndcg")} ndcgCaps ${f("caps")} ild ${f("ild")} junk ${f("junk")}`);
    }
    console.log("\n" + rows.join("\n"));
  });
});
