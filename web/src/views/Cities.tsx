// Every city we cover and how well (idea I-171): the go-live gate's verdict, in plain words, for all to see.
import { useApp } from "../lib/ctx";
import { count } from "../lib/format";
import { build } from "../lib/router";
import type { CitySummary } from "../lib/types";

const PILLARS = ["leagues", "openings_parties", "concerts", "volunteering", "cons_faires", "trivia", "deadlines"];

function Mark({ c, k }: { c: CitySummary; k: string }) {
  const p = c.coverage?.pillars?.[k];
  if (!p) return <td class="muted">–</td>;
  const word = p.state === "strong" ? "Good" : p.state === "thin" ? "Thin" : "None yet";
  return (
    <td class={`pillar-cell ${p.state}`} title={`${p.label}: ${count(p.count)} upcoming`}>
      <span aria-hidden="true">{p.state === "strong" ? "●" : p.state === "thin" ? "◐" : "○"}</span>
      <span class="sr-only">{word}</span>
    </td>
  );
}

export function Cities() {
  const { index } = useApp();
  const cities = [...index.cities].sort((a, b) => a.name.localeCompare(b.name));
  const live = cities.filter((c) => c.tier !== "beta").length;
  const labels = PILLARS.map((k) => cities.find((c) => c.coverage?.pillars?.[k])?.coverage?.pillars?.[k]?.label ?? k);
  return (
    <div class="container">
      <header class="page-head inner">
        <h1>Cities and coverage</h1>
        <p class="lede">
          {cities.length} cities. {live} are live; {cities.length - live} are in beta while we add sources and build up a
          track record. Every city has to clear the same checks before it's called live, and this table shows where each one stands.
        </p>
        <p class="meta">● good coverage · ◐ thin so far · ○ nothing yet. <a class="quiet-link" href={build({ city: null, view: "methodology" })}>How we decide</a></p>
      </header>
      <div class="table-wrap section" style={{ marginTop: "24px" }}>
        <table class="data-table coverage-table">
          <thead>
            <tr>
              <th scope="col">City</th>
              <th scope="col">Status</th>
              <th scope="col" class="num">This week</th>
              <th scope="col" class="num">Sources</th>
              {labels.map((l) => <th scope="col" key={l}>{l}</th>)}
            </tr>
          </thead>
          <tbody>
            {cities.map((c) => (
              <tr key={c.slug}>
                <th scope="row"><a href={build({ city: c.slug, view: "feed" })}>{c.name}</a></th>
                <td>{c.tier === "beta" ? <a class="quiet-link" href={build({ city: c.slug, view: "health" })}>Beta</a> : "Live"}</td>
                <td class="num">{count(c.upcoming_7d)}</td>
                <td class="num">{c.coverage?.sources_healthy ?? c.sources_ok}</td>
                {PILLARS.map((k) => <Mark key={k} c={c} k={k} />)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p class="small muted section">
        Missing something in your city? <a href="https://github.com/lachlanspangler/GetOffTheCouch/issues/new?labels=source-suggestion&title=Source%20suggestion%3A%20" target="_blank" rel="noopener noreferrer">Suggest a source</a>.
      </p>
    </div>
  );
}
