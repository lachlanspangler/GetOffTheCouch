// I-047: league / season registration windows as a timeline — what's open now, what closes next, what starts when.
import { useApp } from "../lib/ctx";
import { collapseSeries } from "../lib/filters";
import { fmtDay } from "../lib/time";
import { eventHref } from "./EventRow";
import type { Event } from "../lib/types";

const DAY = 86_400_000;

export function RegistrationWaves({ events }: { events: Event[] }) {
  const { feed, now } = useApp();
  if (!feed) return null;
  const span = 60 * DAY;
  const t0 = now.getTime() - 3 * DAY;
  const t1 = t0 + span;
  const rows = collapseSeries(events)
    .map((g) => g.event)
    .filter((e) => /^(sports_league|niche)\./.test(e.category) && e.registration?.closes_at)
    .filter((e) => e.registration!.method !== "derived" || !!e.registration!.opens_at)
    .filter((e) => new Date(e.registration!.closes_at!).getTime() >= now.getTime())
    .sort((a, b) => a.registration!.closes_at!.localeCompare(b.registration!.closes_at!))
    // one bar per organizer and closing day (ten identical Volo bars say nothing)
    .filter((e, i, arr) => arr.findIndex((x) => x.sources[0]?.source_id === e.sources[0]?.source_id && x.registration!.closes_at!.slice(0, 10) === e.registration!.closes_at!.slice(0, 10)) === i)
    .slice(0, 10);
  if (!rows.length) return null;
  const x = (t: number) => `${Math.max(0, Math.min(100, ((t - t0) / span) * 100))}%`;
  const ticks = Array.from({ length: 4 }, (_, i) => t0 + ((i + 0.5) * span) / 4);
  return (
    <section class="waves" aria-labelledby="waves-h">
      <h2 id="waves-h">Registration windows</h2>
      <p class="small secondary">Leagues and cons with published dates, over the next eight weeks.</p>
      <div class="waves-axis">
        {ticks.map((t) => (
          <span key={t} style={{ left: x(t) }}>{fmtDay(new Date(t).toISOString(), feed.timezone)}</span>
        ))}
      </div>
      <ul>
        {rows.map((e) => {
          const r = e.registration!;
          const open = r.opens_at ? new Date(r.opens_at).getTime() : Math.min(new Date(e.first_seen).getTime(), now.getTime());
          const close = new Date(r.closes_at!).getTime();
          const start = new Date(e.start).getTime();
          return (
            <li key={e.id}>
              <a class="lbl" href={eventHref(e, feed.city)} title={e.title}>{e.title}</a>
              <div class="wave-track" role="img" aria-label={`Registration open until ${fmtDay(r.closes_at!, feed.timezone)}; starts ${fmtDay(e.start, feed.timezone)}`}>
                <i class="wave-now" style={{ left: x(now.getTime()) }} aria-hidden="true" />
                <span class="wave-bar" style={{ left: x(open), width: `calc(${x(close)} - ${x(open)})` }} title={`Registration until ${fmtDay(r.closes_at!, feed.timezone)}`} />
                {r.early_bird_ends_at && <i class="wave-eb" style={{ left: x(new Date(r.early_bird_ends_at).getTime()) }} title="Early-bird pricing ends" />}
                {start <= t1 && <i class="wave-start" style={{ left: x(start) }} title={`Season starts ${fmtDay(e.start, feed.timezone)}`} />}
              </div>
            </li>
          );
        })}
      </ul>
      <p class="muted small" style={{ marginTop: "8px" }}><span class="key key-bar" /> registration open · {rows.some((e) => e.registration?.early_bird_ends_at) && <><span class="key key-eb" /> early-bird ends · </>}<span class="key key-start" /> season starts</p>
    </section>
  );
}
