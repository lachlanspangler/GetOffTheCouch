import { useEffect, useState } from "preact/hooks";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { loadHealth } from "../lib/data";
import { age } from "../lib/time";
import type { HealthDoc } from "../lib/types";

const STATE: Record<string, { label: string; cls: string; help: string }> = {
  healthy: { label: "Healthy", cls: "ok", help: "Fetched successfully within its freshness SLA" },
  recovering: { label: "Recovering", cls: "warn", help: "Came back after failures; on probation" },
  degraded: { label: "Degraded", cls: "warn", help: "Recent failure or a suspicious drop in results; retrying" },
  quarantined: { label: "Quarantined", cls: "bad", help: "Failed repeatedly; we keep showing its last good data (marked stale) and probe with backoff" },
  disabled: { label: "Needs setup", cls: "off", help: "Waiting on an API key or turned off" },
  never_run: { label: "Not run yet", cls: "off", help: "Scheduled; hasn't run yet" },
};

export function Health() {
  const { feed, index, now } = useApp();
  const [doc, setDoc] = useState<HealthDoc | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    loadHealth().then(setDoc).catch((e: Error) => setErr(e.message));
  }, []);
  const units = (doc?.units ?? []).filter((u) => !feed || u.city === feed.city);
  const counts = units.reduce<Record<string, number>>((m, u) => ({ ...m, [u.state]: (m[u.state] ?? 0) + 1 }), {});
  return (
    <div class="health">
      <header class="view-head">
        <div>
          <h2>Data health{feed ? `: ${feed.city_name}` : ""}</h2>
          <p class="muted">
            Every source is checked on a schedule. If one breaks, we say so here, keep its last good data marked as stale, and fix it on the next
            loop. Pipeline last ran {age(index.generated_at, now)}.
          </p>
        </div>
      </header>
      {err && <p class="notice notice-warn">Couldn't load health data: {err}</p>}
      <div class="health-sum">
        {Object.entries(counts).map(([s, n]) => (
          <span key={s} class={`pill pill-${STATE[s]?.cls ?? "off"}`}>{n} {STATE[s]?.label ?? s}</span>
        ))}
      </div>
      <div class="table-wrap" tabIndex={0} role="region" aria-label="Source health table">
        <table class="health-table">
          <thead>
            <tr><th>Source</th><th>State</th><th>Last success</th><th>Freshness SLA</th><th>Records</th><th>Note</th></tr>
          </thead>
          <tbody>
            {units.map((u) => (
              <tr key={u.source_id + u.city}>
                <td><strong>{u.name}</strong><br /><span class="muted small">{u.source_id}{!feed && ` · ${u.city}`}</span></td>
                <td><span class={`pill pill-${STATE[u.state]?.cls ?? "off"}`} title={STATE[u.state]?.help}>{STATE[u.state]?.label ?? u.state}</span></td>
                <td>{u.last_success_at ? age(u.last_success_at, now) : "never"}{u.stale && u.state !== "disabled" && <span class="badge badge-stale">stale</span>}</td>
                <td>{u.sla_hours}h</td>
                <td>{u.records}</td>
                <td class="small">{u.reason ?? u.last_error ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {doc?.log && doc.log.length > 0 && (
        <section class="panel">
          <h3><Icon name="activity" size={16} /> Recent health events</h3>
          <ul class="log">
            {doc.log
              .filter((l) => !feed || l.unit.endsWith(`@${feed.city}`))
              .slice(0, 30)
              .map((l, i) => (
                <li key={i} class={`log-${l.level}`}>
                  <span class="muted small">{age(l.at, now)}</span> <code>{l.unit}</code> {l.kind}: {l.message}
                </li>
              ))}
          </ul>
        </section>
      )}
    </div>
  );
}
