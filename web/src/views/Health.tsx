// Public data-status page (DESIGN.md §4.13), modeled on status pages: one plain sentence, then the detail.
import { useEffect, useState } from "preact/hooks";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { loadHealth } from "../lib/data";
import { count } from "../lib/format";
import { build } from "../lib/router";
import { age, fmtDay, fmtTime } from "../lib/time";
import type { HealthDoc, HealthUnit } from "../lib/types";

const STATE: Record<string, { label: string; cls: string; help: string }> = {
  healthy: { label: "Operational", cls: "ok", help: "Fetched successfully within its freshness target" },
  recovering: { label: "Recovering", cls: "warn", help: "Back after failures; being watched" },
  degraded: { label: "Delayed", cls: "warn", help: "A recent failure or a suspicious drop in results; retrying" },
  quarantined: { label: "Down", cls: "bad", help: "Failing repeatedly. Its last good listings are still shown, marked as possibly out of date" },
  disabled: { label: "Not connected", cls: "", help: "Waiting on an API key or switched off" },
  never_run: { label: "Not run yet", cls: "", help: "Scheduled; hasn't run yet" },
};

function Table({ units, showCity }: { units: HealthUnit[]; showCity: boolean }) {
  const { now } = useApp();
  const rel = units.some((u) => u.reliability?.score != null);
  return (
    <div class="table-wrap" tabIndex={0} role="region" aria-label="Sources">
      <table class="data-table">
        <thead>
          <tr>
            <th scope="col">Source</th>
            <th scope="col">Status</th>
            <th scope="col">Last success</th>
            <th scope="col">Listings</th>
            {rel && <th scope="col" title="Share of successful runs over 30 days, discounted by rejected records">Reliability</th>}
            <th scope="col">Note</th>
          </tr>
        </thead>
        <tbody>
          {units.map((u) => {
            const st = STATE[u.state] ?? { label: u.state, cls: "", help: "" };
            return (
              <tr key={u.source_id + u.city}>
                <td>
                  <strong>{u.name}</strong>
                  <div class="mono">{u.source_id}{showCity ? ` · ${u.city}` : ""}</div>
                </td>
                <td><span class={`state ${st.cls}`} title={st.help}>{st.label}</span></td>
                <td class="num">{u.last_success_at ? age(u.last_success_at, now) : "Never"}{u.stale && u.state !== "disabled" && <div class="small tone-caution">Behind schedule</div>}</td>
                <td class="num">{count(u.records)}</td>
                {rel && <td class="num">{u.reliability?.score != null ? `${Math.round(u.reliability.score)}%` : "Not enough runs"}</td>}
                <td class="small secondary">{u.reason ?? u.last_error ?? ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Health() {
  const { feed, index, now } = useApp();
  const [doc, setDoc] = useState<HealthDoc | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    loadHealth().then(setDoc).catch((e: Error) => setErr(e.message));
  }, []);
  const all = (doc?.units ?? []).filter((u) => !feed || u.city === feed.city);
  const active = all.filter((u) => u.state !== "disabled");
  const off = all.filter((u) => u.state === "disabled");
  const behind = active.filter((u) => u.stale || u.state === "quarantined" || u.state === "degraded");
  const tz = feed?.timezone ?? "America/New_York";
  const where = feed ? `${feed.city_name} ` : "";
  const sorted = [...active].sort((a, b) => Number(!b.stale) - Number(!a.stale) || a.name.localeCompare(b.name));
  return (
    <div class="container">
      <header class="page-head inner">
        {feed && <ol class="breadcrumb"><li><a href={build({ city: feed.city, view: "feed" })}>{feed.city_name}</a></li><li aria-current="page">Data status</li></ol>}
        <h1>Data status{feed ? `: ${feed.city_name}` : ""}</h1>
        <p class="lede">Every source is checked on a schedule. If one breaks, we say so here and keep showing its last good listings, marked as possibly out of date.</p>
      </header>
      {err && <p class="notice notice-critical"><Icon name="alert" size={16} /> We couldn't load the status data ({err}).</p>}
      {doc && (
        <>
          <p class={`status-banner ${behind.length ? "warn" : "ok"}`} role="status">
            <Icon name={behind.length ? "alert" : "check"} size={20} />
            <span>
              {behind.length
                ? `${behind.length} of ${active.length} ${where}sources are behind. Their last good listings are still shown, marked as possibly out of date.`
                : `All ${active.length} ${where}sources are up to date.`}
            </span>
          </p>
          <p class="small muted" style={{ marginTop: "6px", marginLeft: "32px" }}>Last full rebuild: {fmtDay(index.generated_at, tz)}, {fmtTime(index.generated_at, tz)} ({age(index.generated_at, now)})</p>
          {!feed && (
            <div class="summary-grid">
              {index.cities.map((c) => (
                <div key={c.slug}>
                  <a class="n" href={build({ city: c.slug, view: "health" })} style={{ color: "var(--color-text)", textDecoration: "none" }}>{c.name}</a>
                  <p class="l">{c.sources_ok} of {c.sources_total - (c.sources_disabled ?? 0)} sources up to date</p>
                </div>
              ))}
            </div>
          )}
          <section class="section" aria-labelledby="srcs">
            <h2 id="srcs" style={{ marginBottom: "12px" }}>Sources</h2>
            <Table units={sorted} showCity={!feed} />
          </section>
          {off.length > 0 && (
            <section class="section" aria-labelledby="off">
              <h2 id="off">Not connected yet</h2>
              <p class="secondary" style={{ margin: "6px 0 12px" }}>Built and tested, waiting on an API key, a partner agreement or a terms check. They don't affect the listings above.</p>
              <Table units={off} showCity={!feed} />
            </section>
          )}
          {doc.log.length > 0 && (
            <section class="section" aria-labelledby="log">
              <h2 id="log" style={{ marginBottom: "12px" }}>Recent changes</h2>
              <ul class="log">
                {doc.log
                  .filter((l) => !feed || l.unit.endsWith(`@${feed.city}`))
                  .slice(0, 30)
                  .map((l, i) => (
                    <li key={i}>
                      <span class="muted">{age(l.at, now)}</span> · <span class="mono">{l.unit}</span> · {l.kind}: {l.message}
                    </li>
                  ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
