// Deadlines (DESIGN.md §4.11): the state to-dos first, then published deadlines grouped by how soon.
import { DateBox, StatusLine } from "../components/EventRow";
import { eventHref } from "../components/EventRow";
import { Icon } from "../components/Icon";
import { RegistrationWaves } from "../components/RegistrationWaves";
import { StarterPack } from "../components/StarterPack";
import { useApp } from "../lib/ctx";
import { catLabel } from "../lib/categories";
import { deadlines, DEFAULT_FILTERS, type DeadlineItem } from "../lib/filters";
import { priceLabel } from "../lib/format";
import { calendar, download } from "../lib/ics";
import { cardSignals, closesPhrase } from "../lib/signals";
import { fmtDay } from "../lib/time";
import type { Event } from "../lib/types";
import { build } from "../lib/router";
import { displayTitle, isLeadable } from "../lib/curate";

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

function uniqEvents(items: DeadlineItem[]): Event[] {
  return [...new Map(items.filter((i) => i.kind === "closes").map((i) => [i.event.id, i.event])).values()];
}

function Row({ i, group }: { i: DeadlineItem; group?: DeadlineItem[] }) {
  const { feed, index, now } = useApp();
  const tz = feed!.timezone;
  const e = i.event;
  const sig = cardSignals(e, now);
  const regUrl = e.registration?.url ?? e.offers?.find((o) => o.kind === "registration")?.url;
  const price = priceLabel(e);
  const n = group?.length ?? 1;
  const org = e.organizer ?? feed!.sources?.find((s) => s.source_id === e.sources[0]?.source_id)?.name ?? "";
  const prices = (group ?? [i]).map((g) => g.event.price.min).filter((x): x is number => x != null);
  const what =
    n > 1
      ? [`${n} ${new Set((group ?? []).map((g) => g.event.category)).size === 1 ? catLabel(e.category, index.taxonomy).toLowerCase() : catLabel(e.category.split(".")[0], index.taxonomy).toLowerCase()} sign-ups`, prices.length ? `from $${Math.min(...prices)}` : null].filter(Boolean).join(" · ")
      : [catLabel(e.category, index.taxonomy), `starts ${fmtDay(e.start, tz)}`, price].filter(Boolean).join(" · ");
  const h = i.hours;
  // the date block already says when; only spell it out when it's urgent
  const status = i.kind === "closes" && h <= 48 ? ({ text: `${kindLabel(i.kind, e)} ${closesPhrase(i.at, tz, now)}`, tone: "critical", icon: "clock" } as const) : null;
  const title = n > 1 ? `${org || displayTitle(e.title)}: ${n} sign-ups close ${fmtDay(i.at, tz)}` : displayTitle(e.title);
  const href = n > 1 ? build({ city: feed!.city, view: "feed", filters: { ...DEFAULT_FILTERS, q: "", when: "all", cats: [e.category] } }) : eventHref(e, feed!.city);
  return (
    <li>
      <article class="dlrow" aria-labelledby={`dl-${e.id}-${i.kind}`} data-testid="deadline-row">
        <DateBox iso={i.at} tz={tz} now={now} label={i.kind === "opens" ? "Opens" : "Closes"} />
        <div>
          <h3 id={`dl-${e.id}-${i.kind}`}><a href={href}>{title}</a></h3>
          <p class="what">{what}</p>
          <StatusLine s={status} tag={n === 1 && sig.status?.icon === "users" ? sig.status.text : null} />
        </div>
        {regUrl && n === 1 && (
          <a class="btn btn-secondary btn-sm go" href={regUrl} target="_blank" rel="noopener noreferrer">
            Register ↗<span class="sr-only"> for {e.title} (opens in new tab)</span>
          </a>
        )}
      </article>
    </li>
  );
}

/** Many sign-ups from one organizer closing the same day (e.g. 40 Volo leagues) become one row. */
function groupRows(items: DeadlineItem[], tz: string): { lead: DeadlineItem; group?: DeadlineItem[] }[] {
  const by = new Map<string, DeadlineItem[]>();
  for (const i of items) {
    const k = `${i.event.sources[0]?.source_id ?? ""}|${i.kind}|${fmtDay(i.at, tz)}`;
    by.set(k, [...(by.get(k) ?? []), i]);
  }
  const out: { lead: DeadlineItem; group?: DeadlineItem[] }[] = [];
  const done = new Set<string>();
  for (const i of items) {
    const k = `${i.event.sources[0]?.source_id ?? ""}|${i.kind}|${fmtDay(i.at, tz)}`;
    if (done.has(k)) continue;
    const g = by.get(k)!;
    if (g.length >= 3) {
      done.add(k);
      out.push({ lead: g[0], group: g });
    } else out.push({ lead: i });
  }
  return out;
}

export function Deadlines({ events }: { events: Event[] }) {
  const { feed, now } = useApp();
  if (!feed) return null;
  const all = deadlines(events, now);
  const published = collapse(all.filter((i) => !i.derived && isLeadable(i.event, feed.state)));
  const groups = [
    { id: "week", title: "This week", items: published.filter((i) => i.hours <= 24 * 7) },
    { id: "two", title: "Next two weeks", items: published.filter((i) => i.hours > 24 * 7 && i.hours <= 24 * 21) },
    { id: "later", title: "Later this season", items: published.filter((i) => i.hours > 24 * 21) },
  ];
  const signups = collapse(all.filter((i) => i.derived && i.hours <= 24 * 14 && isLeadable(i.event, feed.state) && i.event.tickets?.spots_left !== 0));
  const nSources = (feed.sources ?? []).filter((s) => s.state !== "disabled").length;
  return (
    <div class="container narrow">
      <header class="page-head inner">
        <h1>Deadlines</h1>
        <p class="lede">League sign-ups, registration cutoffs and early-bird prices in {feed.city_name}, soonest first. Just moved? The <a href="#state">state paperwork deadlines</a> are below.</p>
      </header>
      {!published.length && (
        <div class="empty">
          <h2>No published sign-up deadlines in the next few weeks.</h2>
          <p>We check {nSources} {feed.city_name} sources every few hours. New leagues usually post 4–6 weeks before a season starts.</p>
        </div>
      )}
      {groups.map((g) =>
        g.items.length ? (
          <section key={g.id} class="dl-group" aria-labelledby={`g-${g.id}`}>
            <div class="section-head" style={{ marginBottom: "4px" }}>
              <h2 id={`g-${g.id}`}>{g.title}</h2>
              {g.id === "week" && (
                <button class="btn btn-quiet btn-sm" onClick={() => download(`${feed.city}-deadlines-this-week.ics`, calendar(uniqEvents(g.items), { mode: "deadlines", name: `${feed.city_name} deadlines this week` }))}>
                  <Icon name="calendarPlus" size={16} /> Add {uniqEvents(g.items).length === 1 ? "it" : `these ${uniqEvents(g.items).length}`} to your calendar
                </button>
              )}
            </div>
            <ul class="rows">{groupRows(g.items, feed.timezone).map((r) => <Row key={`${r.lead.event.id}-${r.lead.kind}`} i={r.lead} group={r.group} />)}</ul>
          </section>
        ) : null,
      )}
      <RegistrationWaves events={events} />
      <div id="state" style={{ scrollMarginTop: "80px" }}><StarterPack /></div>
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
                    <h3><a href={eventHref(i.event, feed.city)}>{displayTitle(i.event.title)}</a></h3>
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
