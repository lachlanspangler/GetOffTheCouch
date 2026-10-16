import { useEffect, useRef } from "preact/hooks";
import type { Event } from "../lib/types";
import { useApp } from "../lib/ctx";
import { catIcon, catLabel, hue } from "../lib/categories";
import {
  availabilityLabel,
  bandLabel,
  confidenceWord,
  count,
  estimateLabel,
  OFFER_KIND,
  offerPrice,
  priceLabel,
  sourceName,
  weatherLabel,
} from "../lib/format";
import { calendar, download, slug } from "../lib/ics";
import { age, fmtDateLong, fmtDay, fmtTime, relative } from "../lib/time";
import { DeadlineBadge } from "./EventCard";
import { Icon } from "./Icon";
import { LeafletMap } from "./LeafletMap";
import { Sparkline } from "./Sparkline";

const METHOD_WORD: Record<string, string> = {
  reported: "reported by the source",
  derived: "derived",
  extracted: "extracted from the description",
  estimated: "estimated",
  curated: "verified by hand",
};

export async function share(title: string, url: string): Promise<string> {
  try {
    if (navigator.share) {
      await navigator.share({ title, url });
      return "Shared";
    }
    await navigator.clipboard.writeText(url);
    return "Link copied";
  } catch {
    return "Couldn't share";
  }
}

/** I-052: a prefilled GitHub issue, so corrections need no account system of our own. */
function reportUrl(e: Event): string {
  const body = `Event: ${e.title}\nID: ${e.id}\nCity: ${e.city}\nSources: ${e.sources.map((s) => `${s.source_id} ${s.url ?? ""}`).join(", ")}\n\nWhat's wrong?\n`;
  return `https://github.com/lachlanspangler/GetOffTheCouch/issues/new?labels=data-report&title=${encodeURIComponent(`Data report: ${e.title}`)}&body=${encodeURIComponent(body)}`;
}

export function EventDrawer({ e }: { e: Event }) {
  const { feed, go, index, saved, toggleSave, sourceNames, now, byId } = useApp();
  const ref = useRef<HTMLDivElement>(null);
  const close = () => go({ city: feed?.city ?? e.city, eventId: null });
  useEffect(() => {
    ref.current?.focus();
    const onKey = (ev: KeyboardEvent) => ev.key === "Escape" && close();
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [e.id]);
  const tz = e.timezone;
  const price = priceLabel(e);
  const isSaved = saved.includes(e.id);
  const pins =
    e.location.lat != null && e.location.lon != null
      ? [{ id: e.id, lat: e.location.lat, lon: e.location.lon, hue: hue(e.category), title: e.location.venue_name ?? e.title, sub: e.location.address ?? "" }]
      : [];
  const mapsUrl =
    e.location.lat != null
      ? `https://www.openstreetmap.org/?mlat=${e.location.lat}&mlon=${e.location.lon}#map=17/${e.location.lat}/${e.location.lon}`
      : e.location.address
        ? `https://www.openstreetmap.org/search?query=${encodeURIComponent(e.location.address)}`
        : null;
  const series = (e.series_dates ?? []).filter((d) => d !== e.start);
  const seriesEvents = series
    .map((d) => [...byId.values()].find((x) => x.series_id === e.series_id && x.start === d))
    .filter(Boolean) as Event[];
  const regOffer = e.offers?.find((o) => o.kind === "registration");
  const cta = e.registration?.url
    ? { url: e.registration.url, label: "Register", icon: "check" }
    : regOffer
      ? { url: regOffer.url, label: "Register", icon: "check" }
      : e.offers?.[0]
        ? { url: e.offers[0].url, label: e.offers[0].kind === "rsvp" ? "RSVP" : "Get tickets", icon: "ticket" }
        : e.url
          ? { url: e.url, label: "Event page", icon: "external" }
          : null;
  const shareUrl = `${location.origin}${location.pathname}#/${e.city}/event/${e.id}`;
  return (
    <div class="drawer-wrap" onClick={(ev) => ev.target === ev.currentTarget && close()}>
      <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title" tabIndex={-1} ref={ref} style={{ "--h": hue(e.category) }}>
        <header class="drawer-head">
          <span class="cat">
            <Icon name={catIcon(e.category, index.taxonomy)} size={15} /> {catLabel(e.category, index.taxonomy)}
          </span>
          <button class="icon-btn" onClick={close} aria-label="Close">
            <Icon name="x" />
          </button>
        </header>
        <h2 id="drawer-title">{e.title}</h2>
        {e.stale && (
          <p class="notice notice-warn">
            <Icon name="alert" size={15} /> Possibly out of date: {e.stale_reason}
          </p>
        )}
        <p class="when">
          <Icon name="calendar" size={16} />
          {e.kind === "opening" ? (
            <span>New license {relative(e.start, now)} ({fmtDateLong(e.start, tz)}). This is a signal, not a confirmed opening date.</span>
          ) : (
            <span>
              {fmtDateLong(e.start, tz)}
              {!e.all_day && ` · ${fmtTime(e.start, tz)}${e.end ? `–${fmtTime(e.end, tz)}` : ""}`}
              {e.recurrence && <span class="muted"> · {e.recurrence}</span>}
            </span>
          )}
        </p>
        {(e.location.venue_name || e.location.address) && (
          <p class="where">
            <Icon name="pin" size={16} />
            <span>
              {e.location.venue_name && <strong>{e.location.venue_name}</strong>}
              {e.location.address && e.location.address !== e.location.venue_name && <span class="muted"> · {e.location.address}</span>}
              {mapsUrl && (
                <a class="small" href={mapsUrl} target="_blank" rel="noopener noreferrer">
                  {" "}open map
                </a>
              )}
            </span>
          </p>
        )}

        {e.weather && (
          <p class="where">
            <span aria-hidden="true">{weatherLabel(e.weather)?.slice(0, 2)}</span>
            <span>
              {e.weather.short}
              {e.weather.temp_f != null && `, ${Math.round(e.weather.temp_f)}°F`}
              {e.weather.precip_pct != null && ` · ${Math.round(e.weather.precip_pct)}% chance of precipitation`}
              <span class="muted small"> · National Weather Service forecast, {age(e.weather.fetched_at, now)}</span>
            </span>
          </p>
        )}

        <div class="drawer-actions">
          {cta && (
            <a class="btn" href={cta.url} target="_blank" rel="noopener noreferrer">
              <Icon name={cta.icon} size={16} /> {cta.label}
            </a>
          )}
          <button class="btn btn-ghost" onClick={() => download(`${slug(e.title)}.ics`, calendar([e], { name: e.title }))}>
            <Icon name="calendar" size={16} /> Add to calendar
          </button>
          {e.registration?.closes_at && (
            <button
              class="btn btn-ghost"
              onClick={() => download(`${slug(e.title)}-deadline.ics`, calendar([e], { mode: "deadlines", name: "Deadline" }))}
              title="Calendar reminders 2 days and 3 hours before registration closes"
            >
              <Icon name="bell" size={16} /> Remind me
            </button>
          )}
          <button class={`btn btn-ghost ${isSaved ? "on" : ""}`} aria-pressed={isSaved} onClick={() => toggleSave(e.id)}>
            <Icon name="bookmark" size={16} /> {isSaved ? "Saved" : "Save"}
          </button>
          <button class="btn btn-ghost" onClick={async (ev) => { const t = ev.currentTarget; t.textContent = await share(e.title, shareUrl); }}>
            <Icon name="share" size={16} /> Share
          </button>
        </div>

        {e.registration && (
          <section class="panel">
            <h3>Deadlines</h3>
            <ul class="facts">
              {e.registration.opens_at && <li><span>Registration opens</span><strong>{fmtDay(e.registration.opens_at, tz)} · {relative(e.registration.opens_at, now)}</strong></li>}
              {e.registration.closes_at && <li><span>{e.registration.method === "derived" ? "Register before" : "Register by"}</span><strong>{fmtDay(e.registration.closes_at, tz)} {fmtTime(e.registration.closes_at, tz)} · <DeadlineBadge e={e} compact /></strong></li>}
              {e.registration.early_bird_ends_at && <li><span>Early-bird ends</span><strong>{fmtDay(e.registration.early_bird_ends_at, tz)}</strong></li>}
              {!!e.registration.signup_types?.length && <li><span>Sign up as</span><strong>{e.registration.signup_types.map((s) => s.replace("_", " ")).join(", ")}</strong></li>}
              {!!e.registration.skill_levels?.length && <li><span>Skill level</span><strong>{e.registration.skill_levels.join(", ")}</strong></li>}
            </ul>
            {e.registration.evidence && (
              <blockquote class="evidence">
                “{e.registration.evidence}”
                <cite>{METHOD_WORD[e.registration.method ?? "reported"]}{e.registration.method === "extracted" ? ` · confidence ${confidenceWord(e.registration.confidence ?? 0.6)}` : ""}</cite>
              </blockquote>
            )}
          </section>
        )}

        <section class="panel">
          <h3>Tickets & price</h3>
          <ul class="facts">
            <li><span>Price</span><strong>{price ?? <span class="muted">not listed by any source</span>}{e.price.note && <span class="muted"> · {e.price.note}</span>}</strong></li>
            {availabilityLabel(e.tickets?.availability) && <li><span>Availability</span><strong>{availabilityLabel(e.tickets?.availability)}</strong></li>}
            {e.tickets?.pct_left && (
              <li title={e.tickets.pct_left.method}>
                <span>Tickets left</span>
                <strong>~{Math.round(e.tickets.pct_left.mid)}% <span class="muted">({Math.round(e.tickets.pct_left.low)}–{Math.round(e.tickets.pct_left.high)}%, {confidenceWord(e.tickets.pct_left.confidence)} confidence)</span></strong>
              </li>
            )}
            {e.tickets?.signal && <li><span>Signal</span><strong>{e.tickets.signal}</strong></li>}
          </ul>
          {e.tickets?.pct_left && <p class="muted small">{e.tickets.pct_left.method}</p>}
          {!!e.offers?.length && (
            <table class="offers">
              <thead>
                <tr><th>Seller</th><th>Type</th><th>Price</th><th>Checked</th><th /></tr>
              </thead>
              <tbody>
                {e.offers.map((o) => (
                  <tr key={o.url}>
                    <td>{o.seller}</td>
                    <td>{OFFER_KIND[o.kind]}{o.listing_count != null && <span class="muted"> · {count(o.listing_count)} listings</span>}</td>
                    <td>{offerPrice(o)}{o.fees_included === false && o.price_min != null && <span class="muted"> + fees</span>}</td>
                    <td class="muted">{age(o.fetched_at, now)}</td>
                    <td><a href={o.url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${o.seller}`}><Icon name="external" size={14} /></a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {e.price_trend && <Sparkline points={e.price_trend.points ?? []} />}
        </section>

        <section class="panel">
          <h3>Who'll be there</h3>
          <ul class="facts">
            {e.attendance && (
              <li title={e.attendance.method}>
                <span>Expected crowd</span>
                <strong>{estimateLabel(e.attendance)} <span class="muted">({bandLabel(e.attendance)} · {confidenceWord(e.attendance.confidence)} confidence)</span></strong>
              </li>
            )}
            {e.social && <li><span>Meeting people</span><strong>{Math.round(e.social.score * 10)}/10</strong></li>}
          </ul>
          {e.attendance && <p class="muted small">How we estimate: {e.attendance.method}.</p>}
          {e.social && <p class="muted small">{(e.social.reasons ?? []).join(" · ")}</p>}
        </section>

        {seriesEvents.length > 0 && (
          <section class="panel">
            <h3>More dates</h3>
            <div class="chips">
              {seriesEvents.slice(0, 8).map((x) => (
                <button class="chip" key={x.id} onClick={() => go({ city: x.city, eventId: x.id })}>
                  {fmtDay(x.start, tz)}
                </button>
              ))}
            </div>
          </section>
        )}

        {e.summary && (
          <section class="panel">
            <h3>About</h3>
            <p class="desc">{e.summary}</p>
          </section>
        )}

        {pins.length > 0 && (
          <section class="panel panel-map">
            <LeafletMap center={[pins[0].lat, pins[0].lon]} pins={pins} zoom={15} height="200px" label={`Map of ${e.location.venue_name ?? e.title}`} />
          </section>
        )}

        <section class="panel provenance">
          <h3>Where this came from</h3>
          <ul>
            {e.sources.map((s) => (
              <li key={s.source_id + s.record_id}>
                <strong>{sourceName(s.source_id, sourceNames)}</strong>
                {s.url && (
                  <a href={s.url} target="_blank" rel="noopener noreferrer"> original listing <Icon name="external" size={12} /></a>
                )}
                <span class="muted"> · checked {age(s.fetched_at, now)}</span>
              </li>
            ))}
          </ul>
          {e.provenance && (
            <p class="muted small">
              {Object.entries(e.provenance).map(([field, p]) => `${field}: ${METHOD_WORD[p.method ?? "reported"] ?? p.method} (${sourceName(p.source, sourceNames)})`).join(" · ")}
            </p>
          )}
          <p class="muted small">First seen {age(e.first_seen, now)}. We never invent data: estimates are labeled and always show a range.</p>
          <p class="small">
            <a href={reportUrl(e)} target="_blank" rel="noopener noreferrer">Something wrong? Report it</a>
          </p>
        </section>
      </aside>
    </div>
  );
}
