import { useEffect, useState } from "preact/hooks";
import { EventCard } from "../components/EventCard";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { collapseSeries } from "../lib/filters";
import { dayKey, fmtDateLong } from "../lib/time";
import type { Event } from "../lib/types";

const PAGE = 60;

export function Feed({ events }: { events: Event[] }) {
  const { feed, now, route } = useApp();
  const [limit, setLimit] = useState(PAGE);
  useEffect(() => setLimit(PAGE), [route.filters, feed?.city]);
  if (!feed) return null;
  const tz = feed.timezone;
  const openings = events.filter((e) => e.kind === "opening");
  const regular = events.filter((e) => e.kind !== "opening");
  const allGroups = collapseSeries(regular);
  const groups = allGroups.slice(0, limit);
  const byDay = new Map<string, typeof groups>();
  for (const g of groups) {
    const k = new Date(g.event.start) < now ? dayKey(now, tz) : dayKey(g.event.start, tz);
    byDay.set(k, [...(byDay.get(k) ?? []), g]);
  }
  if (!events.length) {
    return (
      <div class="empty">
        <Icon name="sofa" size={40} />
        <h3>Nothing matches. Couch wins this round.</h3>
        <p class="muted">Try a wider date range or fewer filters.</p>
      </div>
    );
  }
  const today = dayKey(now, tz);
  const tomorrow = dayKey(new Date(now.getTime() + 86_400_000), tz);
  return (
    <div class="feed">
      {[...byDay.entries()].map(([day, gs]) => (
        <section key={day} class="day">
          <h2 class="day-head">
            {day === today ? "Today" : day === tomorrow ? "Tomorrow" : fmtDateLong(gs[0].event.start, tz).replace(/, \d{4}$/, "")}
            <span class="muted"> · {gs.length}</span>
          </h2>
          <div class="grid">
            {gs.map((g) => (
              <EventCard key={g.event.id} e={g.event} more={g.more} />
            ))}
          </div>
        </section>
      ))}
      {allGroups.length > limit && (
        <div class="more">
          <button class="btn btn-ghost" onClick={() => setLimit(limit + PAGE * 2)}>
            Show more ({allGroups.length - limit} left)
          </button>
        </div>
      )}
      {openings.length > 0 && (
        <section class="day">
          <h2 class="day-head">
            New spots in town <span class="muted">· from new liquor & business licenses</span>
          </h2>
          <div class="grid">
            {openings.slice(0, 24).map((e) => (
              <EventCard key={e.id} e={e} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
