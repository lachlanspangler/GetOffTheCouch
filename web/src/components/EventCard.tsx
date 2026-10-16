import type { Event } from "../lib/types";
import { useApp } from "../lib/ctx";
import { catIcon, catLabel, hue } from "../lib/categories";
import { availabilityLabel, estimateLabel, priceLabel, sourceName, weatherLabel } from "../lib/format";
import { age, fmtTime, hoursUntil, monthShort, parts, relative, weekdayShort } from "../lib/time";
import { Icon } from "./Icon";

export function spotsLeft(e: Event): { left: number; cap: number | null } | null {
  const t = e.tickets;
  if (t?.spots_left == null) return null;
  return { left: t.spots_left, cap: t.spots_total ?? null };
}

export function timeLeft(hours: number): string {
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 36) return `${Math.round(hours)} hr`;
  const d = Math.round(hours / 24);
  return `${d} day${d === 1 ? "" : "s"}`;
}

export function DeadlineBadge({ e }: { e: Event; compact?: boolean }) {
  const { now } = useApp();
  const at = e.registration?.closes_at;
  if (!at) return null;
  const spots = spotsLeft(e);
  if (e.registration?.method === "derived") {
    // no published deadline: don't invent a countdown, show what we actually know
    return (
      <span class={`badge ${spots && spots.left <= Math.max(2, (spots.cap ?? 0) * 0.2) ? "badge-hot" : "badge-info"}`} title={e.registration.evidence ?? undefined}>
        <Icon name="clock" size={13} />
        {spots ? (spots.left ? (spots.cap ? `${spots.left} of ${spots.cap} spots left` : `${spots.left} spots left`) : "Full") : "Registration required"}
      </span>
    );
  }
  const h = hoursUntil(at, now);
  if (h < 0) return <span class="badge badge-muted">Registration closed</span>;
  const tone = h <= 48 ? "badge-hot" : h <= 24 * 7 ? "badge-warn" : "badge-info";
  return (
    <span class={`badge ${tone}`} title={e.registration?.evidence ?? undefined}>
      <Icon name="clock" size={13} />
      {timeLeft(h)} left to register
    </span>
  );
}

export function EventCard({ e, more = 0, why }: { e: Event; more?: number; why?: string[] }) {
  const { feed, index, go, saved, toggleSave, sourceNames, now } = useApp();
  const tz = e.timezone;
  const p = parts(e.start, tz);
  const price = priceLabel(e);
  const avail = availabilityLabel(e.tickets?.availability);
  const att = estimateLabel(e.attendance);
  const isSaved = saved.includes(e.id);
  const primary = e.offers?.find((o) => o.kind === "registration") ?? e.offers?.[0];
  const sources = e.sources.map((s) => sourceName(s.source_id, sourceNames));
  const open = () => go({ city: feed?.city ?? e.city, eventId: e.id });
  return (
    <article class="card" style={{ "--h": hue(e.category) }} data-testid="event-card">
      <button class="card-date" onClick={open} aria-label={`Open ${e.title}`}>
        {e.kind === "opening" ? (
          <>
            <span class="m">NEW</span>
            <Icon name="store" size={22} />
          </>
        ) : (
          <>
            <span class="m">{monthShort(e.start, tz)}</span>
            <span class="d">{p.day}</span>
            <span class="w">{weekdayShort(e.start, tz)}</span>
          </>
        )}
      </button>
      <div class="card-body">
        <div class="card-top">
          <span class="cat">
            <Icon name={catIcon(e.category, index.taxonomy)} size={14} />
            {catLabel(e.category, index.taxonomy)}
          </span>
          {e.is_new && <span class="badge badge-new" title="First listed in the last 3 days">New</span>}
          {e.stale && (
            <span class="badge badge-stale" title={e.stale_reason ?? "data may be out of date"}>
              <Icon name="alert" size={12} /> stale
            </span>
          )}
        </div>
        <h3 class="card-title">
          <a href={`#/${feed?.city ?? e.city}/event/${e.id}`} onClick={(ev) => { ev.preventDefault(); open(); }}>
            {e.title}
          </a>
        </h3>
        <p class="card-meta">
          {e.kind === "opening" ? (
            <span>License signal · {relative(e.start, now)}</span>
          ) : (
            <span>{e.all_day ? "All day" : fmtTime(e.start, tz)}</span>
          )}
          {(e.location.venue_name || e.location.neighborhood) && (
            <span class="venue">
              <Icon name="pin" size={13} />
              {e.location.venue_name ?? e.location.neighborhood}
            </span>
          )}
        </p>
        <div class="badges">
          <DeadlineBadge e={e} compact />
          {price ? <span class={`badge ${price === "Free" ? "badge-free" : ""}`}>{price}</span> : null}
          {e.tickets?.spots_left != null && e.registration?.method !== "derived" && (
            <span class={`badge ${e.tickets.spots_left <= 2 ? "badge-hot" : "badge-info"}`}>
              {e.tickets.spots_left === 0 ? "Full" : `${e.tickets.spots_left}${e.tickets.spots_total ? ` of ${e.tickets.spots_total}` : ""} spots left`}
            </span>
          )}
          {e.tickets?.selling_fast && (
            <span class="badge badge-hot" title={e.tickets.signal ?? ""}>
              <Icon name="flame" size={12} /> Selling fast
            </span>
          )}
          {avail && avail !== "No ticket needed" && avail !== "On sale" && <span class="badge">{avail}</span>}
          {att && e.kind !== "opening" && (e.attendance?.confidence ?? 0) >= 0.4 && (
            <span class="badge badge-ghost" title={e.attendance?.method}>
              <Icon name="users" size={12} /> {att}
            </span>
          )}
          {(e.social?.score ?? 0) >= 0.75 && (
            <span class="badge badge-social" title={e.social?.reasons?.join(" · ")}>
              Meet people
            </span>
          )}
          {e.weather && (
            <span class="badge badge-ghost" title={`NWS forecast: ${e.weather.short}`}>
              {weatherLabel(e.weather)}
            </span>
          )}
          {more > 0 && <span class="badge badge-ghost">+{more} more date{more > 1 ? "s" : ""}</span>}
        </div>
        {why && why.length > 0 && (
          <p class="why">
            <Icon name="sparkles" size={13} /> {why.slice(0, 3).join(" · ")}
          </p>
        )}
        <div class="card-foot">
          <span class="src" title={`via ${sources.join(", ")} · last checked ${e.last_checked}`}>
            <span class="src-name">
              via {sources.slice(0, 2).join(" + ")}
              {sources.length > 2 ? ` +${sources.length - 2}` : ""}
            </span>
            <span class="src-age">· {age(e.last_checked, now)}</span>
          </span>
          <span class="actions">
            <button
              class={`icon-btn ${isSaved ? "on" : ""}`}
              aria-pressed={isSaved}
              aria-label={isSaved ? "Unsave" : "Save"}
              onClick={() => toggleSave(e.id)}
            >
              <Icon name="bookmark" size={16} />
            </button>
            {primary && (
              <a class="btn btn-small" href={primary.url} target="_blank" rel="noopener noreferrer">
                {primary.kind === "registration" ? "Register" : primary.kind === "rsvp" ? "RSVP" : "Tickets"}
                <Icon name="external" size={13} />
              </a>
            )}
          </span>
        </div>
      </div>
    </article>
  );
}
