// Honest per-city coverage from the go-live gate (ADR-0008): what a city is strong in, and what's still thin.
import type { CityCoverage } from "../lib/types";

const ORDER = ["leagues", "openings_parties", "concerts", "volunteering", "cons_faires", "trivia", "deadlines"];

export function strongestText(c: CityCoverage | undefined): string | null {
  if (!c?.strongest?.length || !c.pillars) return null;
  const labels = c.strongest.map((k) => c.pillars![k]?.label.toLowerCase()).filter(Boolean);
  if (!labels.length) return null;
  return labels.length === 1 ? labels[0] : `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`;
}

export function CoverageStrip({ c }: { c: CityCoverage }) {
  if (!c.pillars) return null;
  const keys = ORDER.filter((k) => c.pillars![k]);
  return (
    <ul class="coverage" aria-label="What we cover here">
      {keys.map((k) => {
        const p = c.pillars![k];
        const word = p.state === "strong" ? "good coverage" : p.state === "thin" ? "thin so far" : "nothing yet";
        return (
          <li key={k} class={`pillar ${p.state}`} title={p.note ?? `${p.count} upcoming`}>
            <i aria-hidden="true" />
            {p.label}
            <span class="sr-only">: {word}</span>
          </li>
        );
      })}
    </ul>
  );
}
