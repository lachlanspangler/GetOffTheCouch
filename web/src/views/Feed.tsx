// The city page: an editorial landing (picks, closing soon) over the day-grouped event list. Hubs
// (/chicago/concerts/) reuse it with their own headline.
import { useEffect, useMemo, useState } from "preact/hooks";
import { CompactRow, EventRow, FeaturedCard, SkeletonRows } from "../components/EventRow";
import { FilterBar, activeCount } from "../components/FilterBar";
import { Icon } from "../components/Icon";
import { Art } from "../components/Art";
import { useApp } from "../lib/ctx";
import { coverage } from "../lib/coverage";
import { collapseSeries, deadlines, DEFAULT_FILTERS, isOngoing } from "../lib/filters";
import { count } from "../lib/format";
import { hubTitle } from "../lib/title";
import { forYou, highlights, type Profile } from "../lib/recommend";
import { usePersistent } from "../lib/store";
import { WhyThis } from "../components/WhyThis";
import { strongestText } from "../components/Coverage";
import { build } from "../lib/router";
import { HUB_BY_SLUG, HUBS, url } from "../lib/site";
import { closesPhrase } from "../lib/signals";
import { age, dayKey, dayHeader, weekendRange } from "../lib/time";
import type { Event } from "../lib/types";
import { familyOf } from "../lib/art";
import { isAdminRole, isCampusOnly, isKids, isLeadable, isUnderway } from "../lib/curate";

const PAGE = 50;

function hubTitleOrCity(hub: string | null | undefined, city: string, now: Date, tz: string): string {
  return hub ? hubTitle(hub, city, now, tz) : city;
}

export function cityHeadline(hub: string | null | undefined, city: string): string {
  const h = hub ? HUB_BY_SLUG.get(hub) : undefined;
  if (!h) return city;
  return h.cats ? `${h.label} in ${city}` : `${h.label} in ${city}`;
}

function DayGroups({ events, limit, hide, onMore }: { events: Event[]; limit: number; hide: Set<string>; onMore: () => void }) {
  const { feed, now } = useApp();
  if (!feed) return null;
  const tz = feed.timezone;
  const groups = collapseSeries(events).filter((g) => !hide.has(g.event.id));
  const shown = groups.slice(0, limit);
  const byDay = new Map<string, typeof shown>();
  for (const g of shown) {
    const k = new Date(g.event.start) < now ? dayKey(now, tz) : dayKey(g.event.start, tz);
    byDay.set(k, [...(byDay.get(k) ?? []), g]);
  }
  const t = (e: Event) => new Date(e.start).getTime();
  for (const gs of byDay.values()) gs.sort((a, b) => Number(isAllDay(a.event)) - Number(isAllDay(b.event)) || t(a.event) - t(b.event));
  return (
    <>
      {[...byDay.entries()].map(([day, gs]) => {
        const h = dayHeader(day, tz, now);
        return (
          <section key={day} class="day-group" aria-labelledby={`d-${day}`}>
            <h2 class="day-head" id={`d-${day}`}>
              {h.label}
              {h.date && <span class="date">{h.date}</span>}
              <span class="n">{gs.length}</span>
            </h2>
            <ul class="rows">
              {gs.map((g) => <EventRow key={g.event.id} e={g.event} more={g.more} />)}
            </ul>
          </section>
        );
      })}
      <More total={groups.length} shown={shown.length} onMore={onMore} />
    </>
  );
}

function isAllDay(e: Event): boolean {
  return !!e.all_day;
}

function More({ total, shown, onMore }: { total: number; shown: number; onMore: () => void }) {
  if (total <= shown) return null;
  return (
    <div class="more-row">
      <button class="btn btn-secondary" onClick={onMore}>Show {Math.min(PAGE, total - shown)} more</button>
      <span class="small muted">Showing {count(shown)} of {count(total)}</span>
    </div>
  );
}

function ClosingSoon({ events, n = 4 }: { events: Event[]; n?: number }) {
  const { feed, now } = useApp();
  if (!feed) return null;
  const items = deadlines(events, now).filter((d) => !d.derived && d.kind === "closes" && d.hours <= 24 * 14 && isLeadable(d.event, feed.state));
  const seen = new Set<string>();
  const uniq = items.filter((d) => (seen.has(d.event.series_id ?? d.event.id) ? false : (seen.add(d.event.series_id ?? d.event.id), true))).slice(0, n);
  if (!uniq.length) return null;
  return (
    <section>
      <h2>Closing soon</h2>
      <ul class="rows">
      {uniq.map((d) => (
        <CompactRow key={d.event.id} e={d.event} time="" sub={`Registration closes ${closesPhrase(d.at, feed.timezone, now)}`} />
      ))}
      </ul>
      <p class="small" style={{ marginTop: "10px" }}><a class="more-link" href={build({ city: feed.city, view: "deadlines" })}>All deadlines →</a></p>
    </section>
  );
}

export function Feed({ events }: { events: Event[] }) {
  const { feed, now, route, labels, index } = useApp();
  const [limit, setLimit] = useState(PAGE);
  useEffect(() => setLimit(PAGE), [route.filters, feed?.city, route.hub]);
  const f = route.filters;
  const hub = route.hub ? HUB_BY_SLUG.get(route.hub) : undefined;
  const unfiltered = !hub && !f.q && activeCount(f) === 0 && f.when === DEFAULT_FILTERS.when;
  const tops = useMemo(() => (feed && unfiltered ? highlights(feed.events.filter((e) => isLeadable(e, feed.state)), labels, now, 3) : []), [feed, unfiltered, now]);
  const [profile] = usePersistent<Profile | null>(`profile:${feed?.city ?? "_"}`, null);
  const { neighborhoods, saved } = useApp();
  const personal = useMemo(() => {
    if (!feed || !unfiltered || !(profile?.interests.length || saved.length)) return [];
    const topIds = new Set(tops.map((s) => s.event.id));
    return forYou(feed.events, profile, labels, neighborhoods, now, 8).filter((s) => !topIds.has(s.event.id)).slice(0, 6);
  }, [feed, unfiltered, profile, saved.length, tops, now]);
  if (!feed) return <div class="container"><SkeletonRows /></div>;
  const cov = coverage(feed, index.taxonomy, now);
  const summary = index.cities.find((c) => c.slug === feed.city);
  // Kids' programs, board/admin volunteer roles and campus club meetings stay one filter away, not in the lead.
  const wantsKids = f.cats.some((c) => c === "family" || c.startsWith("family.")) || f.tags.includes("kids_teens");
  const wantsVolunteer = f.cats.some((c) => c === "volunteer" || c.startsWith("volunteer."));
  const searching = !!f.q;
  const hiddenKids = searching || wantsKids ? 0 : events.filter((e) => e.kind !== "opening" && isKids(e)).length;
  const shown = events.filter((e) => searching || ((wantsKids || !isKids(e)) && (wantsVolunteer || !isAdminRole(e)) && !isCampusOnly(e)));
  const openings = shown.filter((e) => e.kind === "opening");
  const ongoing = shown.filter((e) => e.kind !== "opening" && isOngoing(e, now));
  const regular = shown.filter((e) => e.kind !== "opening" && !isOngoing(e, now) && !isUnderway(e, now));
  const topIds = new Set(tops.length >= 3 ? tops.map((s) => s.event.id) : []);
  const wk = weekendRange(now, feed.timezone);
  const stale = (feed.sources ?? []).filter((s) => s.stale && s.state !== "disabled");
  return (
    <div class="container">
      <header class="page-head">
        {hub && (
          <ol class="breadcrumb">
            <li><a href={build({ city: feed.city, view: "feed" })}>{feed.city_name}</a></li>
            <li aria-current="page">{hub.label}</li>
          </ol>
        )}
        <h1>
          {hubTitleOrCity(route.hub, feed.city_name, now, feed.timezone)}
          {summary?.tier === "beta" && <span class="beta-chip" title="We're still adding sources here">Beta</span>}
        </h1>
        <p class="lede">
          {hub?.when === "weekend"
            ? `${wk.label}. Leagues, shows, parties and volunteer shifts, from ${summary?.coverage?.sources_healthy ?? cov.sources} local sources.`
            : hub
              ? `Upcoming ${hub.label.toLowerCase()} in ${feed.city_name}, from official calendars and venues, checked every few hours.`
              : "What's on this week, and what's due."}
        </p>
        <p class="meta">
          Updated {age(index.generated_at, now)} · {summary?.coverage ? `${summary.coverage.sources_healthy} sources${strongestText(summary.coverage) ? `, strongest in ${strongestText(summary.coverage)}` : ""}` : cov.text}
          {" · "}<a class="quiet-link" href={build({ city: feed.city, view: "health" })}>Data status</a>
        </p>
        {!hub && summary?.coverage?.pillars && (() => {
          const thin = Object.values(summary.coverage.pillars).filter((p) => p.state === "none").map((p) => p.label.toLowerCase());
          return thin.length ? <p class="meta">Still thin here: {thin.join(", ")}. We're adding sources.</p> : null;
        })()}
      </header>
      {summary?.tier === "beta" && !hub && (
        <p class="notice" role="note">
          <Icon name="info" size={16} />
          <span>{feed.city_name} is new here. We're still adding sources, so some categories are thin. What's listed is real and checked; it's just not everything yet.</span>
        </p>
      )}
      {summary?.coverage?.banner && summary.tier !== "beta" && (
        <p class="notice notice-caution" role="note">
          <Icon name="alert" size={16} />
          <span>Coverage in {feed.city_name} has dropped below our usual bar. {summary.coverage.reasons?.[0] ?? ""} <a href={build({ city: feed.city, view: "health" })}>Details</a></span>
        </p>
      )}
      {stale.length > 0 && (
        <p class="notice notice-caution" role="status">
          <Icon name="alert" size={16} />
          <span>
            {stale.length === 1 ? "1 source" : `${stale.length} sources`} may be out of date.{" "}
            <a href={build({ city: feed.city, view: "health" })}>Details</a>
          </span>
        </p>
      )}
      {tops.length >= 3 && (
        <section class="section" aria-labelledby="picks">
          <div class="section-head">
            <div>
              <h2 id="picks">Picks this week</h2>
            </div>
          </div>
          <div class="featured">
            {[...tops].sort((a, b) => a.event.start.localeCompare(b.event.start)).map((s) => (
              <FeaturedCard key={s.event.id} e={s.event} scored={s} />
            ))}
          </div>
        </section>
      )}
      {personal.length > 0 && (
        <section class="section" aria-labelledby="foryou">
          <div class="section-head">
            <div>
              <h2 id="foryou">For you</h2>
              <p class="small">Based on {profile?.interests.length ? "what you told us you like" : "what you've saved"}. Worked out on this device.</p>
            </div>
            <a class="more-link" href={build({ city: feed.city, view: "plan" })}>{profile?.interests.length ? "Change interests" : "Tell us what you like"}</a>
          </div>
          <ul class="rows">
            {personal.map((s) => (
              <li key={s.event.id} class="foryou-row">
                <EventRow e={s.event} dated bare />
                <WhyThis s={s} profile={profile} />
              </li>
            ))}
          </ul>
        </section>
      )}
      <div class="with-rail">
        <div>
          {unfiltered && (
            <h2 class="section" id="all" style={{ marginBottom: "0" }}>All upcoming events</h2>
          )}
          <FilterBar resultCount={regular.length + ongoing.length} />
          {!regular.length && !ongoing.length ? (
            <div class="empty">
              <h2>Nothing matches these filters.</h2>
              <p>Try a wider date range or remove a filter.</p>
              {(activeCount(f) > 0 || f.q) && (
                <a class="btn btn-secondary" href={build({ city: feed.city, view: "feed", filters: { ...DEFAULT_FILTERS, when: f.when } })}>Clear filters</a>
              )}
            </div>
          ) : (
            <DayGroups events={regular} limit={limit} hide={topIds} onMore={() => setLimit(limit + PAGE)} />
          )}
          {hiddenKids > 0 && (
            <p class="small secondary" style={{ marginTop: "16px" }}>
              {hiddenKids.toLocaleString("en-US")} family and kids' events aren't shown here. <a href={url(`${feed.city}/family/`)}>See family events</a>
            </p>
          )}
          {ongoing.length > 0 && (
            <details class="day-group quiet-sec">
              <summary>
                <h2 class="day-head">Ongoing <span class="date">exhibits, faires and multi-day events</span><span class="n">{collapseSeries(ongoing).length}</span></h2>
              </summary>
              <ul class="rows">
                {collapseSeries(ongoing).slice(0, 48).map((g) => <EventRow key={g.event.id} e={g.event} more={g.more} dated />)}
              </ul>
            </details>
          )}
          {openings.length > 0 && (
            <section class="day-group" aria-labelledby="openings">
              <h2 class="day-head" id="openings">New bars and restaurants <span class="date">from new liquor and business licenses</span><span class="n">{openings.length}</span></h2>
              <ul class="rows">
                {openings.slice(0, 24).map((e) => <EventRow key={e.id} e={e} />)}
              </ul>
            </section>
          )}
        </div>
        <aside class="rail" aria-label="Closing soon and more">
          <ClosingSoon events={feed.events} n={5} />
          <section>
            <h2>Browse {feed.city_name}</h2>
            <ul class="rows">
              {HUBS.filter((h) => h.cats).slice(0, 9).map((h) => (
                <li key={h.slug} class="crow" style={{ gridTemplateColumns: "1fr" }}>
                  <span class="ti"><a href={url(`${feed.city}/${h.slug}/`)}>{h.label}</a></span>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
      {unfiltered && (
        <>
          <section class="section" aria-labelledby="browse">
            <div class="section-head"><h2 id="browse">Browse by category</h2></div>
            <div class="cat-tiles">
              {HUBS.filter((h) => h.cats).map((h) => {
                const n = feed.events.filter((e) => e.kind !== "opening" && !isUnderway(e, now) && new Date(e.start).getTime() < now.getTime() + 30 * 86_400_000 && h.cats!.some((c) => e.category === c || e.category.startsWith(`${c}.`))).length;
                if (n < 3) return null;
                return (
                  <div class="tile" key={h.slug}>
                    <Art id={`${feed.city}:${h.slug}`} family={familyOf(h.cats![0])} ratio="4/3" />
                    <h3><a href={url(`${feed.city}/${h.slug}/`)}>{h.label}</a></h3>
                    <p class="sub">{count(n)} upcoming</p>
                  </div>
                );
              })}
            </div>
          </section>
          <section class="section callout" aria-labelledby="newhere">
            <div>
              <h2 id="newhere">New in {feed.city_name}?</h2>
              <p>Tell us what you like and when you moved. We'll put together your first month: a weekly habit, a league to join, the state deadlines and a few things to try.</p>
            </div>
            <a class="btn btn-secondary btn-lg" href={build({ city: feed.city, view: "plan" })}>Make a plan</a>
          </section>
        </>
      )}
    </div>
  );
}
