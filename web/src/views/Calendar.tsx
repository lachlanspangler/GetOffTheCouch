// Month grid + agenda for the selected day (DESIGN.md §4.10). The grid is a real table with arrow-key navigation.
import { useEffect, useRef } from "preact/hooks";
import { CompactRow } from "../components/EventRow";
import { FilterBar } from "../components/FilterBar";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { collapseSeries, isOngoing } from "../lib/filters";
import { displayTitle, isLeadable } from "../lib/curate";
import { dayKey, fmtDateLong, parts } from "../lib/time";
import type { Event } from "../lib/types";

const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const pad = (n: number) => String(n).padStart(2, "0");

function addDays(key: string, n: number): string {
  const d = new Date(`${key}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
}

export function Calendar({ events }: { events: Event[] }) {
  const { feed, route, go, now } = useApp();
  const grid = useRef<HTMLTableElement>(null);
  const focusSel = useRef(false);
  const tz = feed?.timezone ?? "UTC";
  const todayKey = dayKey(now, tz);
  const sel = route.day ?? todayKey;
  useEffect(() => {
    if (focusSel.current) {
      grid.current?.querySelector<HTMLButtonElement>(`[data-day="${sel}"]`)?.focus();
      focusSel.current = false;
    }
  }, [sel]);
  if (!feed) return null;
  const today = parts(now, tz);
  const [year, month] = sel.split("-").map(Number);
  const first = new Date(Date.UTC(year, month - 1, 1, 12));
  const startWd = first.getUTCDay();
  const daysIn = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const byDay = new Map<string, Event[]>();
  for (const e of events) {
    if (e.kind === "opening" || !isLeadable(e, feed?.state)) continue;
    const k = dayKey(e.start, tz);
    byDay.set(k, [...(byDay.get(k) ?? []), e]);
  }
  const key = (d: number) => `${year}-${pad(month)}-${pad(d)}`;
  const shift = (n: number) => {
    const d = new Date(Date.UTC(year, month - 1 + n, 1, 12));
    go({ day: `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-01` }, true);
  };
  const monthName = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" }).format(first);
  const selAll = collapseSeries(byDay.get(sel) ?? []);
  const selOngoing = selAll.filter((g) => isOngoing(g.event, new Date(`${sel}T12:00:00Z`)) || g.event.all_day);
  const selTimed = selAll.filter((g) => !selOngoing.includes(g));
  const cells: (number | null)[] = [...Array.from({ length: startWd }, () => null), ...Array.from({ length: daysIn }, (_, i) => i + 1)];
  while (cells.length % 7) cells.push(null);
  const allWeeks = Array.from({ length: cells.length / 7 }, (_, i) => cells.slice(i * 7, i * 7 + 7));
  // in the current month, start at this week: past weeks are just empty boxes
  const thisMonth = today.year === year && today.month === month;
  const weeks = thisMonth ? allWeeks.filter((wk) => wk.some((d) => d != null && d >= today.day - today.weekday) || wk.every((d) => d == null)) : allWeeks;
  const counts = [...byDay.values()].map((v) => collapseSeries(v).length).sort((a, b) => a - b);
  const q = (p: number) => counts[Math.floor(p * (counts.length - 1))] ?? 0;
  const [q1, q2] = [q(0.33), q(0.66)];
  const onKey = (e: KeyboardEvent) => {
    const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7, PageUp: -30, PageDown: 30 }[e.key];
    if (step) {
      e.preventDefault();
      focusSel.current = true;
      go({ day: addDays(sel, step) }, true);
    }
  };
  const long = (k: string) => new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(`${k}T12:00:00Z`));
  return (
    <div class="container">
      <header class="page-head inner">
        <h1>Calendar</h1>
        <p class="lede">Everything in {feed.city_name} by day. Pick a day to see what's on.</p>
      </header>
      <FilterBar resultCount={events.filter((e) => e.kind !== "opening").length} noWhen />
      <div class="cal-layout">
        <div>
          <div class="cal-nav">
            <h2 aria-live="polite">{monthName}</h2>
            <button class="icon-btn" onClick={() => shift(-1)} aria-label="Previous month"><Icon name="left" /></button>
            <button class="icon-btn" onClick={() => shift(1)} aria-label="Next month"><Icon name="right" /></button>
            <button class="btn btn-quiet btn-sm" onClick={() => go({ day: todayKey }, true)}>Today</button>
          </div>
          <table class="cal-table" ref={grid} onKeyDown={onKey} aria-label={monthName}>
            <thead>
              <tr>{WD.map((w) => <th key={w} scope="col" abbr={w}>{w}</th>)}</tr>
            </thead>
            <tbody>
              {weeks.map((wk, wi) => (
                <tr key={wi}>
                  {wk.map((d, di) => {
                    if (d == null) return <td key={di} class={di === 0 || di === 6 ? "wkend" : ""} />;
                    const k = key(d);
                    const evs = collapseSeries(byDay.get(k) ?? []);
                    const isToday = today.year === year && today.month === month && today.day === d;
                    const past = k < todayKey;
                    const dots = evs.length === 0 ? 0 : evs.length <= q1 ? 1 : evs.length <= q2 ? 2 : 3;
                    const top = evs.find((g) => !g.event.all_day) ?? evs[0];
                    return (
                      <td key={di} class={di === 0 || di === 6 ? "wkend" : ""}>
                        <button
                          class={`cal-cell ${isToday ? "today" : ""} ${past ? "past" : ""}`}
                          data-day={k}
                          tabIndex={k === sel ? 0 : -1}
                          aria-pressed={k === sel}
                          aria-label={`${long(k)}, ${evs.length} event${evs.length === 1 ? "" : "s"}`}
                          onClick={() => go({ day: k }, true)}
                        >
                          <span class="dn">{d}</span>
                          {top && <span class="ev">{displayTitle(top.event.title)}</span>}
                          {evs.length > 1 && <span class="more">{evs.length} events</span>}
                          <span class="dots" aria-hidden="true">{Array.from({ length: dots }, (_, i) => <i key={i} />)}</span>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p class="small muted" style={{ marginTop: "8px" }}>Times are in {feed.city_name} time.<span class="kbd-hint"> Use the arrow keys to move between days.</span></p>
        </div>
        <section class="cal-agenda" aria-labelledby="agenda-h">
          <h2 id="agenda-h">{fmtDateLong(`${sel}T12:00:00Z`, "UTC").replace(/, \d{4}$/, "")}</h2>
          {selAll.length ? (
            <>
              <ul class="rows">
                {selTimed.map((g) => <CompactRow key={g.event.id} e={g.event} sub={g.event.location.venue_name ?? undefined} />)}
              </ul>
              {selOngoing.length > 0 && (
                <details class="quiet-sec" open={!selTimed.length} style={{ marginTop: "16px" }}>
                  <summary class="small" style={{ fontWeight: 600 }}>All day and ongoing ({selOngoing.length})</summary>
                  <ul class="rows">
                    {selOngoing.map((g) => <CompactRow key={g.event.id} e={g.event} time="" sub={g.event.location.venue_name ?? undefined} />)}
                  </ul>
                </details>
              )}
            </>
          ) : (
            <p class="secondary">Nothing listed on this day{events.length < (feed.events.length) ? " with these filters" : ""}.</p>
          )}
        </section>
      </div>
    </div>
  );
}
