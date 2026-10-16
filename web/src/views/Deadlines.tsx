// Deadlines (DESIGN.md §4.11): the state to-dos first, then published deadlines grouped by how soon.
import { DateBox, StatusLine } from "../components/EventRow";
import { eventHref } from "../components/EventRow";
import { Icon } from "../components/Icon";
import { RegistrationWaves } from "../components/RegistrationWaves";
import { StarterPack } from "../components/StarterPack";
import { useApp } from "../lib/ctx";
import { catLabel } from "../lib/categories";
import { deadlines, type DeadlineItem } from "../lib/filters";
import { priceLabel } from "../lib/format";
import { calendar, download } from "../lib/ics";
import { cardSignals, closesPhrase } from "../lib/signals";
import { fmtDay } from "../lib/time";
import type { Event } from "../lib/types";
import { build } from "../lib/router";

const KIND = { closes: "Registration closes", early_bird: "Early-bird price ends", opens: "Registration opens" };

function kindLabel(kind: keyof typeof KIND, e: { category: string }): string {
  if (kind === "opens" && /^(music|nightlife\.comedy|arts\.theater|sports_watch)/.test(e.category)) return "Tickets go on sale";
  return KIND[kind];
}

function collapse(items: DeadlineItem[]): DeadlineItem[] {
  const seen = new Set<string>();
  return items.filter((i) => {
    const k = `${i.event.series_id ?? i.event.id}:${i.kind}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

function Row({ i }: { i: DeadlineItem }) {
  const { feed, index, now } = useApp();
  const tz = feed!.timezone;
  const e = i.event;
  const sig = cardSignals(e, now);
  const regUrl = e.registration?.url ?? e.offers?.find((o) => o.kind === "registration")?.url;
  const price = priceLabel(e);
  const what = [catLabel(e.category, index.taxonomy), `starts ${fmtDay(e.start, tz)}`, price].filter(Boolean).join(" · ");
  const h = i.hours;
  const tone = i.kind === "closes" && h <= 48 ? "critical" : i.kind === "closes" && h <= 24 * 14 ? "caution" : "secondary";
  const status = { text: `${kindLabel(i.kind, e)} ${closesPhrase(i.at, tz, now)}`, tone, icon: "clock" } as const;
  return (
    <li>
      <article class="dlrow" aria-labelledby={`dl-${e.id}-${i.kind}`} data-testid="deadline-row">
        <DateBox iso={i.at} tz={tz} now={now} label={i.kind === "opens" ? "Opens" : "Closes"} />
        <div>
          <h3 id={`dl-${e.id}-${i.kind}`}><a href={eventHref(e, feed!.city)}>{e.title}</a></h3>
          <p class="what">{what}</p>
          <StatusLine s={status} tag={sig.status?.icon === "users" ? sig.status.text : null} />
          {e.registration?.method === "extracted" && <p class="small muted" style={{ marginTop: "2px" }}>Read from the listing text</p>}
        </div>
        {regUrl && (
          <a class="btn btn-secondary btn-sm go" href={regUrl} target="_blank" rel="noopener noreferrer">
            Register ↗<span class="sr-only"> for {e.title} (opens in new tab)</span>
          </a>
        )}
      </article>
    </li>
  );
}

export function Deadlines({ events }: { events: Event[] }) {
  const { feed, now } = useApp();
  if (!feed) return null;
  const all = deadlines(events, now);
  const published = collapse(all.filter((i) => !i.derived));
  const groups = [
    { id: "week", title: "This week", items: published.filter((i) => i.hours <= 24 * 7) },
    { id: "two", title: "Next two weeks", items: published.filter((i) => i.hours > 24 * 7 && i.hours <= 24 * 21) },
    { id: "later", title: "Later this season", items: published.filter((i) => i.hours > 24 * 21) },
  ];
  const signups = collapse(all.filter((i) => i.derived && i.hours <= 24 * 14));
  const withDeadlines = [...new Map(published.filter((i) => i.kind === "closes").map((i) => [i.event.id, i.event])).values()];
  const nSources = (feed.sources ?? []).filter((s) => s.state !== "disabled").length;
  return (
    <div class="container narrow">
      <header class="page-head inner">
        <h1>Deadlines</h1>
        <p class="lede">League sign-ups, registration cutoffs and early-bird prices in {feed.city_name}, soonest first.</p>
        {withDeadlines.length > 0 && (
          <div class="actions">
            <button class="btn btn-secondary" onClick={() => download(`${feed.city}-deadlines.ics`, calendar(withDeadlines, { mode: "deadlines", name: `${feed.city_name} deadlines` }))}>
              <Icon name="calendarPlus" size={16} /> Add all {withDeadlines.length} to your calendar
            </button>
          </div>
        )}
      </header>
      <StarterPack />
      {!published.length && (
        <div class="empty">
          <h2>No published sign-up deadlines in the next few weeks.</h2>
          <p>We check {nSources} {feed.city_name} sources every few hours. New leagues usually post 4–6 weeks before a season starts.</p>
        </div>
      )}
      {groups.map((g) =>
        g.items.length ? (
          <section key={g.id} class="dl-group" aria-labelledby={`g-${g.id}`}>
            <h2 id={`g-${g.id}`}>{g.title}</h2>
            <ul class="rows">{g.items.map((i) => <Row key={`${i.event.id}-${i.kind}`} i={i} />)}</ul>
          </section>
        ) : null,
      )}
      <RegistrationWaves events={events} />
      {signups.length > 0 && (
        <section class="dl-group" aria-labelledby="g-ongoing">
          <h2 id="g-ongoing">Ongoing sign-ups</h2>
          <p>No published deadline: register before it starts. {signups.length} start in the next two weeks.</p>
          <ul class="rows">
            {signups.slice(0, 40).map((i) => (
              <li key={i.event.id}>
                <article class="dlrow">
                  <DateBox iso={i.event.start} tz={feed.timezone} now={now} label="Starts" />
                  <div>
                    <h3><a href={eventHref(i.event, feed.city)}>{i.event.title}</a></h3>
                    <StatusLine s={cardSignals(i.event, now).status} />
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p class="small muted section">
        Deadlines come from registration fields, or from phrases like "register by Nov 3" in the listing, and we show the sentence. If a
        listing only says "registration required", we never invent a countdown. <a href={build({ city: null, view: "methodology" })}>How we find deadlines</a>
      </p>
    </div>
  );
}
