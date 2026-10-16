import { EventCard } from "../components/EventCard";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { hue } from "../lib/categories";
import { collapseSeries } from "../lib/filters";
import { dayKey, fmtDateLong, parts } from "../lib/time";
import type { Event } from "../lib/types";

const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function Calendar({ events }: { events: Event[] }) {
  const { feed, route, go, now } = useApp();
  if (!feed) return null;
  const tz = feed.timezone;
  const today = parts(now, tz);
  const sel = route.day ?? dayKey(now, tz);
  const [sy, sm] = sel.split("-").map(Number);
  const year = sy, month = sm; // month shown = month of the selected day
  const first = new Date(Date.UTC(year, month - 1, 1, 12));
  const startWd = first.getUTCDay();
  const daysIn = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const byDay = new Map<string, Event[]>();
  for (const e of events) {
    if (e.kind === "opening") continue;
    const k = dayKey(e.start, tz);
    byDay.set(k, [...(byDay.get(k) ?? []), e]);
  }
  const key = (d: number) => `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const shift = (n: number) => {
    const d = new Date(Date.UTC(year, month - 1 + n, 1, 12));
    go({ day: `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-01` }, true);
  };
  const monthName = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" }).format(first);
  const selEvents = collapseSeries(byDay.get(sel) ?? []);
  return (
    <div class="calendar-view">
      <div class="cal">
        <header class="cal-head">
          <button class="icon-btn" onClick={() => shift(-1)} aria-label="Previous month"><Icon name="left" /></button>
          <h2>{monthName}</h2>
          <button class="icon-btn" onClick={() => shift(1)} aria-label="Next month"><Icon name="right" /></button>
        </header>
        <div class="cal-grid" aria-label={monthName}>
          {WD.map((w) => <div class="cal-wd" key={w} aria-hidden="true">{w}</div>)}
          {Array.from({ length: startWd }, (_, i) => <div key={`b${i}`} class="cal-cell blank" />)}
          {Array.from({ length: daysIn }, (_, i) => {
            const d = i + 1;
            const k = key(d);
            const evs = byDay.get(k) ?? [];
            const isToday = today.year === year && today.month === month && today.day === d;
            const past = k < dayKey(now, tz);
            return (
              <button
                key={k}
                class={`cal-cell ${k === sel ? "on" : ""} ${isToday ? "today" : ""} ${past ? "past" : ""}`}
                onClick={() => go({ day: k }, true)}
                aria-label={`${new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" }).format(new Date(`${k}T12:00:00Z`))}: ${evs.length} event${evs.length === 1 ? "" : "s"}`}
                aria-pressed={k === sel}
              >
                <span class="cal-d">{d}</span>
                {evs.length > 0 && (
                  <span class="cal-dots">
                    {evs.slice(0, 4).map((e) => <i key={e.id} style={{ "--h": hue(e.category) }} />)}
                    {evs.length > 4 && <b>+{evs.length - 4}</b>}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
      <section class="cal-list">
        <h3>{fmtDateLong(`${sel}T12:00:00Z`, "UTC")}</h3>
        {selEvents.length ? (
          <div class="grid one">
            {selEvents.map((g) => <EventCard key={g.event.id} e={g.event} more={g.more} />)}
          </div>
        ) : (
          <p class="muted">Nothing on this day (with your filters).</p>
        )}
      </section>
    </div>
  );
}
