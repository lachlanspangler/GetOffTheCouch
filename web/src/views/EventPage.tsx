// The event page (DESIGN.md §4.8): a real, bookmarkable page with a sticky "ticket card" and the full
// provenance story next to the call to action.
import { useEffect, useRef, useState } from "preact/hooks";
import { Art } from "../components/Art";
import { CompactRow, eventHref, isDateOnly, StatusLine, Swatch } from "../components/EventRow";
import { Icon } from "../components/Icon";
import { LeafletMap } from "../components/LeafletMap";
import { Sparkline } from "../components/Sparkline";
import { familyOf } from "../lib/art";
import { catLabel } from "../lib/categories";
import { useApp } from "../lib/ctx";
import { loadDetails } from "../lib/data";
import type { EventDetail } from "../lib/details.generated";
import { bandLabel, confidenceWord, count, OFFER_KIND, offerPrice, sourceName } from "../lib/format";
import { calendar, download, slug } from "../lib/ics";
import { similar } from "../lib/recommend";
import { build } from "../lib/router";
import { cardSignals } from "../lib/signals";
import { absolute, eventPath } from "../lib/site";
import { age, fmtDateLong, fmtDay, fmtTime, fmtTimeRange, relative } from "../lib/time";
import type { Event } from "../lib/types";
import { REPO } from "../components/Footer";
import { whyThis } from "../lib/why";
import { displayPlace, displayTitle, displayVenue } from "../lib/curate";

const METHOD_WORD: Record<string, string> = {
  reported: "reported by the source",
  derived: "worked out from the source's data",
  extracted: "read from the listing text",
  estimated: "estimated",
  curated: "checked by hand",
};

export async function share(title: string, link: string): Promise<string> {
  try {
    if (navigator.share) {
      await navigator.share({ title, url: link });
      return "Shared";
    }
    await navigator.clipboard.writeText(link);
    return "Link copied";
  } catch {
    return "Couldn't share";
  }
}

/** A prefilled GitHub issue, so corrections need no account system of our own. */
export function reportUrl(e: Event): string {
  const body = `Event: ${e.title}\nLink: ${absolute(eventPath(e.city, e.id, e.title))}\nID: ${e.id}\nCity: ${e.city}\nSources: ${e.sources.map((s) => `${s.source_id} ${s.url ?? ""}`).join(", ")}\n\nWhat's wrong?\n`;
  return `${REPO}/issues/new?labels=data-report&title=${encodeURIComponent(`Data report: ${e.title}`)}&body=${encodeURIComponent(body)}`;
}

function host(u: string): string {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return "the organizer's site";
  }
}

interface Cta {
  url: string;
  label: string;
  dest: string;
}

export function primaryCta(e: Event, sourceNames: Record<string, string>): Cta | null {
  const reg = e.registration?.url ? { url: e.registration.url, kind: "registration", seller: null as string | null } : null;
  const offer = e.offers?.find((o) => o.kind === "registration") ?? e.offers?.find((o) => o.kind === "primary") ?? e.offers?.[0];
  const pick = reg ?? (offer ? { url: offer.url, kind: offer.kind, seller: offer.seller } : e.url ? { url: e.url, kind: "info", seller: null } : null);
  if (!pick) return null;
  const dest = pick.seller ?? sourceName(e.sources[0]?.source_id ?? "", sourceNames) ?? host(pick.url);
  const verb = pick.kind === "registration" ? "Register" : pick.kind === "rsvp" ? "RSVP" : pick.kind === "primary" || pick.kind === "resale" ? "Get tickets" : "View listing";
  const prep = verb === "Register" ? "with" : "on";
  return { url: pick.url, label: `${verb} ${prep} ${dest}`, dest: host(pick.url) };
}

export function EventPage({ e }: { e: Event }) {
  const { feed, index, sourceNames, now, byId } = useApp();
  const h1 = useRef<HTMLHeadingElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const [detail, setDetail] = useState<EventDetail | null>(null);
  const [showSticky, setShowSticky] = useState(false);
  const [more, setMore] = useState(false);
  const [shareMsg, setShareMsg] = useState<string | null>(null);
  useEffect(() => {
    setDetail(null);
    loadDetails(e.city)
      .then((d) => setDetail(d.events[e.id] ?? null))
      .catch(() => setDetail(null)); // the page still works; provenance just stays summarized
    h1.current?.focus({ preventScroll: true });
    scrollTo(0, 0);
  }, [e.id]);
  useEffect(() => {
    const el = ctaRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([x]) => setShowSticky(!x.isIntersecting && x.boundingClientRect.top < 0));
    io.observe(el);
    return () => io.disconnect();
  }, [e.id]);
  const tz = e.timezone;
  const sig = cardSignals(e, now);
  const summary = detail?.summary ?? e.summary;
  const provenance = detail?.provenance ?? e.provenance;
  const cta = primaryCta(e, sourceNames);
  const city = feed?.city ?? e.city;
  const ended = new Date(e.end ?? e.start).getTime() < now.getTime() - 3 * 3600_000;
  const hasMap = e.location.lat != null && e.location.lon != null;
  const mapsUrl = hasMap
    ? `https://www.openstreetmap.org/?mlat=${e.location.lat}&mlon=${e.location.lon}#map=17/${e.location.lat}/${e.location.lon}`
    : e.location.address
      ? `https://www.openstreetmap.org/search?query=${encodeURIComponent(e.location.address)}`
      : null;
  const directions = hasMap ? `https://www.openstreetmap.org/directions?route=%3B${e.location.lat}%2C${e.location.lon}` : null;
  const seriesEvents = (e.series_dates ?? [])
    .filter((d) => d !== e.start)
    .map((d) => [...byId.values()].find((x) => x.series_id === e.series_id && x.start === d))
    .filter(Boolean) as Event[];
  const sims = similar(e, [...byId.values()], now, 5);
  const why = whyThis(e, now);
  const sellers = new Set((e.offers ?? []).map((o) => o.seller));
  const when = e.kind === "opening" ? null : isDateOnly(e) ? (e.all_day ? "All day" : "Time not listed") : fmtTimeRange(e.start, e.end, tz);
  const shareUrl = absolute(eventPath(city, e.id, e.title));
  const doShare = async () => setShareMsg(await share(e.title, shareUrl));
  const ics = () => download(`${slug(e.title)}.ics`, calendar([e], { name: e.title }));
  const tags = (e.tags ?? []).map((t) => index.tags[t]).filter(Boolean);
  return (
    <div class="container event-page">
      <ol class="breadcrumb">
        <li><a href={build({ city, view: "feed" })}>{feed?.city_name ?? city}</a></li>
        <li>{catLabel(e.category.split(".")[0], index.taxonomy)}</li>
        <li aria-current="page">{catLabel(e.category, index.taxonomy)}</li>
      </ol>
      {ended && (
        <p class="notice notice-caution ended" role="status">
          <Icon name="info" size={16} />
          <span>This event has ended. <a href={build({ city, view: "feed" })}>See what's on in {feed?.city_name ?? city} this week</a>.</span>
        </p>
      )}
      {e.stale && (
        <p class="notice notice-caution" role="status">
          <Icon name="alert" size={16} />
          <span><strong>Listing may be out of date.</strong> {e.stale_reason} We're showing the last version we got.</span>
        </p>
      )}
      <div class="event-grid">
          <header class="event-head">
            <Art id={e.id} family={familyOf(e.category)} ratio="21/9" />
            <p class="cat"><Swatch category={e.category} /> {catLabel(e.category, index.taxonomy)}</p>
            <h1 ref={h1} tabIndex={-1}>{displayTitle(e.title)}</h1>
            {(displayPlace(e, feed?.city_name) || e.location.neighborhood) && (
              <p class="where">{[displayPlace(e, feed?.city_name), e.location.neighborhood].filter(Boolean).join(" · ")}</p>
            )}
          </header>
          <div class="event-sections">
            {summary && (
              <section aria-labelledby="about">
                <h2 id="about">About</h2>
                <p class={`prose-block ${more ? "" : "clamp"}`}>{summary}</p>
                {summary.length > 600 && (
                  <button class="link-btn small" style={{ marginTop: "8px" }} onClick={() => setMore(!more)}>{more ? "Show less" : "Read more"}</button>
                )}
                {e.organizer && <p class="small secondary" style={{ marginTop: "12px" }}>Organized by {e.organizer}</p>}
              </section>
            )}
            {why.length > 0 && (
              <section aria-labelledby="why">
                <h2 id="why">Why it's here</h2>
                <ul class="why-list">{why.map((w) => <li key={w}>{w}</li>)}</ul>
              </section>
            )}
            <section aria-labelledby="gtk">
              <h2 id="gtk">Good to know</h2>
              <dl class="facts">
                {e.weather && (
                  <div>
                    <dt>Weather</dt>
                    <dd>
                      {e.weather.short}{e.weather.temp_f != null && `, ${Math.round(e.weather.temp_f)}°F`}
                      {e.weather.precip_pct != null && e.weather.precip_pct >= 20 && `, ${Math.round(e.weather.precip_pct)}% chance of rain`}
                      <span class="how">National Weather Service forecast, {age(e.weather.fetched_at, now)}</span>
                    </dd>
                  </div>
                )}
                {e.attendance && e.attendance.confidence >= 0.45 && (
                  <div>
                    <dt>Expected crowd</dt>
                    <dd>
                      About {bandLabel(e.attendance)} people
                      <span class="how">Estimated ({confidenceWord(e.attendance.confidence)} confidence): {e.attendance.method}</span>
                    </dd>
                  </div>
                )}
                {e.social && (
                  <div>
                    <dt>Meeting people</dt>
                    <dd>
                      {e.social.score >= 0.75 ? "Very good" : e.social.score >= 0.5 ? "Good" : "So-so"} for meeting people
                      {!!e.social.reasons?.length && <span class="how">{e.social.reasons.map((r) => r.charAt(0).toUpperCase() + r.slice(1)).join(". ")}.</span>}
                    </dd>
                  </div>
                )}
                {tags.length > 0 && (
                  <div>
                    <dt>Details</dt>
                    <dd>{tags.join(" · ")}</dd>
                  </div>
                )}
                {e.recurrence && (
                  <div>
                    <dt>Repeats</dt>
                    <dd>{e.recurrence.replace(/\b(am|pm)\b/g, (m) => m.toUpperCase())}</dd>
                  </div>
                )}
              </dl>
            </section>
            {e.registration && (e.registration.closes_at || e.registration.opens_at || e.registration.evidence) && (
              <section aria-labelledby="reg">
                <h2 id="reg">Registration</h2>
                <dl class="facts">
                  {e.registration.opens_at && (
                    <div><dt>{/^(music|nightlife\.comedy|arts\.theater|sports_watch)/.test(e.category) ? "Tickets on sale" : "Registration opens"}</dt><dd>{fmtDay(e.registration.opens_at, tz)}, {fmtTime(e.registration.opens_at, tz)} <span class="how">{relative(e.registration.opens_at, now)}</span></dd></div>
                  )}
                  {e.registration.closes_at && e.registration.method !== "derived" && (
                    <div><dt>Registration closes</dt><dd>{fmtDay(e.registration.closes_at, tz)}, {fmtTime(e.registration.closes_at, tz)} <span class="how">{relative(e.registration.closes_at, now)}</span></dd></div>
                  )}
                  {e.registration.closes_at && e.registration.method === "derived" && (
                    <div><dt>Deadline</dt><dd>No published deadline. Register before it starts; spots fill as people sign up.</dd></div>
                  )}
                  {e.registration.early_bird_ends_at && <div><dt>Early-bird price ends</dt><dd>{fmtDay(e.registration.early_bird_ends_at, tz)}</dd></div>}
                  {e.tickets?.spots_left != null && (
                    <div><dt>Spots</dt><dd>{e.tickets.spots_left === 0 ? "Full" : `${count(e.tickets.spots_left)}${e.tickets.spots_total ? ` of ${count(e.tickets.spots_total)}` : ""} left`}<span class="how">Reported by the source</span></dd></div>
                  )}
                  {!!e.registration.signup_types?.length && <div><dt>Sign up as</dt><dd>{e.registration.signup_types.map((s) => s.replace("_", " ")).join(", ")}</dd></div>}
                  {!!e.registration.skill_levels?.length && <div><dt>Skill level</dt><dd>{e.registration.skill_levels.join(", ")}</dd></div>}
                </dl>
                {e.registration.evidence && (
                  <blockquote class="quote">
                    “{e.registration.evidence}”
                    <cite>{METHOD_WORD[e.registration.method ?? "reported"]}{e.registration.method === "extracted" ? `, ${confidenceWord(e.registration.confidence ?? 0.6)} confidence` : ""}</cite>
                  </blockquote>
                )}
              </section>
            )}
            {((e.offers ?? []).some((o) => o.price_min != null || o.listing_count != null) || (e.price_trend && (e.price_trend.window_hours ?? 0) >= 24) || e.tickets?.pct_left) && (
              <section aria-labelledby="prices">
                <h2 id="prices">Prices</h2>
                {!!e.offers?.length && (
                  <div class="table-wrap">
                    <table class="data-table">
                      <thead><tr><th scope="col">Seller</th><th scope="col">Type</th><th scope="col">From</th><th scope="col">Checked</th><th scope="col"><span class="sr-only">Link</span></th></tr></thead>
                      <tbody>
                        {e.offers.map((o) => (
                          <tr key={o.url}>
                            <td>{o.seller}</td>
                            <td>{OFFER_KIND[o.kind]}{o.listing_count != null && <span class="muted"> · {count(o.listing_count)} listings</span>}</td>
                            <td class="num">{offerPrice(o)}{o.fees_included === false && o.price_min != null && <span class="muted"> + fees</span>}</td>
                            <td class="muted">{age(o.fetched_at, now)}</td>
                            <td><a href={o.url} target="_blank" rel="noopener noreferrer">Open<span class="sr-only"> {o.seller} (opens in new tab)</span> ↗</a></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {e.tickets?.pct_left && (
                  <p class="small secondary" style={{ marginTop: "12px" }}>
                    About {Math.round(e.tickets.pct_left.mid)}% of tickets left ({Math.round(e.tickets.pct_left.low)}–{Math.round(e.tickets.pct_left.high)}%, {confidenceWord(e.tickets.pct_left.confidence)} confidence). {e.tickets.pct_left.method}
                  </p>
                )}
                {e.price_trend && (e.price_trend.window_hours ?? 0) >= 24 && <Sparkline points={e.price_trend.points ?? []} />}
              </section>
            )}
            {(hasMap || e.location.address) && (
              <section aria-labelledby="loc" class="event-map">
                <h2 id="loc">Location</h2>
                <p style={{ marginBottom: "12px" }}>
                  {e.location.venue_name && <strong>{e.location.venue_name}</strong>}
                  {e.location.address && e.location.address !== e.location.venue_name && <span class="secondary">{e.location.venue_name ? <br /> : null}{e.location.address}</span>}
                  {(e.location.geocode_confidence ?? 1) < 0.5 && <span class="small muted"><br />Approximate location</span>}
                </p>
                {hasMap && (
                  <LeafletMap center={[e.location.lat!, e.location.lon!]} pins={[{ id: e.id, lat: e.location.lat!, lon: e.location.lon!, hue: 0, title: e.location.venue_name ?? e.title, sub: e.location.address ?? "" }]} zoom={15} label={`Map of ${e.location.venue_name ?? e.title}`} still />
                )}
                <p class="links">
                  {mapsUrl && <a href={mapsUrl} target="_blank" rel="noopener noreferrer">Open in OpenStreetMap ↗</a>}
                  {directions && <a href={directions} target="_blank" rel="noopener noreferrer">Directions ↗</a>}
                </p>
              </section>
            )}
            {seriesEvents.length > 0 && (
              <section aria-labelledby="dates">
                <h2 id="dates">More dates</h2>
                <ul class="chips" style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {seriesEvents.slice(0, 12).map((x) => (
                    <li key={x.id}><a class="chip" href={eventHref(x, city)}>{fmtDay(x.start, tz)}{isDateOnly(x) ? "" : `, ${fmtTime(x.start, tz)}`}</a></li>
                  ))}
                </ul>
              </section>
            )}
            <section aria-labelledby="src">
              <h2 id="src">Where this comes from</h2>
              <ul class="sources-list">
                {e.sources.map((s) => (
                  <li key={s.source_id + s.record_id}>
                    <strong>{sourceName(s.source_id, sourceNames)}</strong>
                    <span class="muted"> · checked {age(s.fetched_at, now)}</span>
                    {s.url && <> · <a href={s.url} target="_blank" rel="noopener noreferrer">Original listing<span class="sr-only"> (opens in new tab)</span> ↗</a></>}
                  </li>
                ))}
              </ul>
              {provenance && Object.keys(provenance).length > 0 && (
                <p class="small muted" style={{ marginTop: "12px" }}>
                  {Object.entries(provenance).map(([field, p]) => `${field[0].toUpperCase()}${field.slice(1)} ${METHOD_WORD[p.method ?? "reported"] ?? p.method} (${sourceName(p.source, sourceNames)})`).join(". ")}.
                </p>
              )}
              <p class="small muted" style={{ marginTop: "8px" }}>
                First listed {age(e.first_seen, now)}. We never make up details: estimates are labeled and always come with a range. <a href={build({ city: null, view: "methodology" })}>How we get the data</a>.
              </p>
              <p class="small" style={{ marginTop: "12px" }}>
                <a href={reportUrl(e)} target="_blank" rel="noopener noreferrer"><Icon name="flag" size={14} /> Report a problem with this listing</a>
              </p>
            </section>
            {sims.length > 0 && (
              <section aria-labelledby="sim">
                <h2 id="sim">Similar this week</h2>
                <ul class="rows">
                  {sims.map((x) => <CompactRow key={x.id} e={x} time={`${fmtDay(x.start, tz)}`} sub={displayPlace(x, feed?.city_name) ?? undefined} />)}
                </ul>
              </section>
            )}
          </div>
        <div class="ticket-col">
          <aside class="ticket" aria-label="Date, place and tickets">
            <dl>
              <div class="when">
                <dt>When</dt>
                <dd>
                  {e.kind === "opening" ? (
                    <>New license {relative(e.start, now)} ({fmtDay(e.start, tz)}). A signal, not a confirmed opening date.</>
                  ) : (
                    <>
                      <strong>{fmtDateLong(e.start, tz).replace(/, \d{4}$/, "")}</strong>
                      {when && <span class="tnum" style={{ display: "block" }}>{when}</span>}
                    </>
                  )}
                </dd>
              </div>
              {(displayVenue(e, feed?.city_name) || e.location.address) && (
                <div>
                  <dt>Where</dt>
                  <dd>
                    {displayVenue(e, feed?.city_name) ?? displayPlace(e, feed?.city_name)}
                    {displayVenue(e, feed?.city_name) && e.location.address && <span class="small secondary" style={{ display: "block" }}>{e.location.address}</span>}
                  </dd>
                </div>
              )}
              <div>
                <dt>Price</dt>
                <dd>
                  {sig.price ? <strong class={sig.price === "Free" ? "free" : ""}>{sig.price}</strong> : <span class="secondary">Not listed by the source</span>}
                  {e.price.note && !(e.price.is_free && /free/i.test(e.price.note)) && <span class="small secondary"> · {e.price.note}</span>}
                  {sellers.size > 0 && sig.price && sig.price !== "Free" && <span class="small secondary" style={{ display: "block" }}>via {[...sellers].join(", ")}</span>}
                </dd>
              </div>
            </dl>
            <StatusLine s={sig.status} />
            <div class="actions" ref={ctaRef}>
              {cta && !ended && (
                <a class="btn btn-lg btn-block" href={cta.url} target="_blank" rel="noopener noreferrer">
                  {cta.label} ↗<span class="sr-only"> (opens in new tab)</span>
                </a>
              )}
              <div class="row">
                <SaveToggle e={e} />
                <button class="btn btn-secondary" onClick={ics}><Icon name="calendarPlus" size={16} /> Add to calendar</button>
              </div>
              <button class="btn btn-quiet" onClick={doShare}><Icon name="share" size={16} /> {shareMsg ?? "Share"}</button>
              {(e.registration?.closes_at && e.registration.method !== "derived") || (e.registration?.opens_at && new Date(e.registration.opens_at) > now) ? (
                <button class="btn btn-quiet" onClick={() => download(`${slug(e.title)}-deadline.ics`, calendar([e], { mode: "deadlines", name: "Deadline" }))}>
                  <Icon name="bell" size={16} /> Remind me before the deadline
                </button>
              ) : null}
            </div>
            {cta && <p class="fine">We don't sell tickets or take sign-ups. You'll finish on {cta.dest}.</p>}
          </aside>
        </div>
      </div>
      {cta && !ended && (
        <div class={`sticky-cta ${showSticky ? "show" : ""}`} aria-hidden={!showSticky}>
          <span class="price">{sig.price ?? e.title}</span>
          <a class="btn" href={cta.url} target="_blank" rel="noopener noreferrer" tabIndex={showSticky ? 0 : -1}>{cta.label.split(" ")[0] === "Get" ? "Get tickets" : cta.label.split(" ")[0]} ↗</a>
        </div>
      )}
    </div>
  );
}

function SaveToggle({ e }: { e: Event }) {
  const { saved, toggleSave } = useApp();
  const on = saved.includes(e.id);
  return (
    <button class="btn btn-secondary" aria-pressed={on} onClick={() => toggleSave(e.id)}>
      <Icon name="bookmark" size={16} /> {on ? "Saved" : "Save"}
    </button>
  );
}

export function eventTitle(e: Event): string {
  return `${e.title} · ${fmtDay(e.start, e.timezone)}`;
}

