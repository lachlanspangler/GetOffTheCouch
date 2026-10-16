// Dev aid, skipped unless GOTC_PEEK=city,persona (or junk[,persona]): v1/v2 top 10 with judged grades.
import { describe, it } from "vitest";
import { CITIES, grade, judgments, persona, PERSONAS, runV1, runV2, snapshot } from "./evalLib";
import type { Scored } from "../../src/lib/rank/index";

const PEEK = process.env.GOTC_PEEK;

describe.skipIf(!PEEK)("peek", () => {
  it("prints", () => {
    const [city, pid] = PEEK!.split(",");
    if (city === "junk") {
      // every grade-0 item in any v2 top 10, for error analysis
      for (const c of CITIES)
        for (const q of pid ? [pid] : PERSONAS) {
          const sn = snapshot(c);
          const jj = judgments(c);
          for (const x of runV2(sn, persona(q, c)))
            if (grade(jj, x.event, q) === 0) console.log(`${c} ${q} | ${x.event.title.slice(0, 60)} [${x.event.category}] ${x.event.sources[0].source_id}${x.slot ? " <" + x.slot + ">" : ""}`);
        }
      return;
    }
    const s = snapshot(city);
    const j = judgments(city);
    const p = persona(pid, city);
    const show = (l: Scored[]) =>
      l
        .map((x) => {
          const top = Object.entries(x.contrib ?? {})
            .filter(([, c]) => Math.abs(c) >= 0.15)
            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
            .map(([k, c]) => `${k}${c > 0 ? "+" : ""}${c.toFixed(2)}`)
            .join(" ");
          return `  g=${grade(j, x.event, pid) ?? "?"} ${x.score.toFixed(2)} ${x.event.title.slice(0, 50)} [${x.event.category}] ${x.event.sources[0].source_id}${x.slot ? " <" + x.slot + ">" : ""} | ${top}`;
        })
        .join("\n");
    console.log(`v1\n${show(runV1(s, p))}\nv2\n${show(runV2(s, p))}`);
  });
});
