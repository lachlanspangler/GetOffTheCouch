import { DeadlineBadge } from "../components/EventCard";
import { Icon } from "../components/Icon";
import { RegistrationWaves } from "../components/RegistrationWaves";
import { StarterPack } from "../components/StarterPack";
import { useApp } from "../lib/ctx";
import { catIcon, catLabel, hue } from "../lib/categories";
import { deadlines, type DeadlineItem, urgency } from "../lib/filters";
import { calendar, download } from "../lib/ics";
import { fmtDay, fmtTime } from "../lib/time";
import type { Event } from "../lib/types";

const SECTION = {
  now: { title: "Next 48 hours", tone: "hot" },
  soon: { title: "This week", tone: "warn" },
  week: { title: "This month", tone: "info" },
  later: { title: "Later", tone: "muted" },
} as const;

const KIND = { closes: "Registration closes", early_bird: "Early-bird pricing ends", opens: "Registration opens" };

function kindLabel(kind: keyof typeof KIND, e: { category: string }): string {
  if (kind === "opens" && /^(music|nightlife\.comedy|arts\.theater|sports_watch)/.test(e.category)) return "Tickets go on sale";
  return KIND[kind];
}

function countdown(hours: number): string {
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m`;
  if (hours < 48) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

function collapseSeriesItems(items: DeadlineItem[]): DeadlineItem[] {
  const seen = new Set<string>();
  return items.filter((i) => {
    const k = i.event.series_id ?? i.event.id;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

export function Deadlines({ events }: { events: Event[] }) {
  const { feed, index, go, now } = useApp();
  if (!feed) return null;
  const all = deadlines(events, now);
  const items = all.filter((i) => !i.derived);
  const signups = collapseSeriesItems(all.filter((i) => i.derived && i.hours <= 24 * 14));
  const sections = (["now", "soon", "week", "later"] as const).map((u) => ({ u, items: items.filter((i) => urgency(i.hours) === u) }));
  const withDeadlines = [...new Map(items.filter((i) => i.kind === "closes").map((i) => [i.event.id, i.event])).values()];
  return (
    <div class="deadlines">
      <header class="view-head">
        <div>
          <h2>Deadlines you'd otherwise miss</h2>
          <p class="muted">League signups, registration cutoffs, early-bird pricing and volunteer signups, sorted by urgency.</p>
        </div>
        {withDeadlines.length > 0 && (
          <button class="btn" onClick={() => download(`${feed.city}-deadlines.ics`, calendar(withDeadlines, { mode: "deadlines", name: `${feed.city_name} deadlines` }))}>
            <Icon name="bell" size={16} /> Add all {withDeadlines.length} to my calendar
          </button>
        )}
      </header>
      <RegistrationWaves events={events} />
      <StarterPack />
      {!items.length && (
        <div class="empty">
          <Icon name="check" size={36} />
          <h3>No open deadlines right now</h3>
          <p class="muted">We pull deadlines from registration pages and descriptions ("register by Oct 3"). More league sources are on the way.</p>
        </div>
      )}
      {sections.map(
        ({ u, items }) =>
          items.length > 0 && (
            <section key={u} class={`dl-section dl-${SECTION[u].tone}`}>
              <h3>
                {SECTION[u].title} <span class="muted">· {items.length}</span>
              </h3>
              <ul class="dl-list">
                {items.map((i) => (
                  <li key={`${i.event.id}-${i.kind}`} class="dl-row" style={{ "--h": hue(i.event.category) }}>
                    <span class="dl-count" aria-label={`${Math.round(i.hours)} hours left`}>{countdown(i.hours)}</span>
                    <div class="dl-body">
                      <span class="dl-kind">{kindLabel(i.kind, i.event)} · {fmtDay(i.at, feed.timezone)} {fmtTime(i.at, feed.timezone)}</span>
                      <button class="dl-title" onClick={() => go({ city: feed.city, eventId: i.event.id })}>{i.event.title}</button>
                      <span class="cat small">
                        <Icon name={catIcon(i.event.category, index.taxonomy)} size={13} /> {catLabel(i.event.category, index.taxonomy)}
                        {i.event.registration?.method === "extracted" && <span class="muted"> · read from the listing text</span>}
                      </span>
                    </div>
                    {i.kind === "closes" && <DeadlineBadge e={i.event} compact />}
                    {(i.event.registration?.url || i.event.offers?.find((o) => o.kind === "registration")) && (
                      <a class="btn btn-small" target="_blank" rel="noopener noreferrer" href={i.event.registration?.url ?? i.event.offers!.find((o) => o.kind === "registration")!.url}>
                        Register <Icon name="external" size={13} />
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ),
      )}
      {signups.length > 0 && (
        <details class="dl-section dl-muted signups">
          <summary>
            <h3>Sign up before it starts <span class="muted">· {signups.length} in the next 2 weeks · no published deadline</span></h3>
          </summary>
          <ul class="dl-list">
            {signups.slice(0, 60).map((i) => (
              <li key={i.event.id} class="dl-row" style={{ "--h": hue(i.event.category) }}>
                <span class="dl-count">{countdown(i.hours)}</span>
                <div class="dl-body">
                  <span class="dl-kind">Starts {fmtDay(i.event.start, feed.timezone)} {fmtTime(i.event.start, feed.timezone)}</span>
                  <button class="dl-title" onClick={() => go({ city: feed.city, eventId: i.event.id })}>{i.event.title}</button>
                  <span class="cat small"><Icon name={catIcon(i.event.category, index.taxonomy)} size={13} /> {catLabel(i.event.category, index.taxonomy)}</span>
                </div>
                <DeadlineBadge e={i.event} />
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
