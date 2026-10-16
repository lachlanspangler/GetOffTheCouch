// The three card variants (DESIGN.md §4.5): list row, compact row, featured card. All read cardSignals(),
// so a card never shows more than one meta line, one status line and one tag.
import type { ComponentChildren } from "preact";
import { useApp } from "../lib/ctx";
import { catLabel } from "../lib/categories";
import { familyOf, ART_HUE } from "../lib/art";
import { cardSignals, type Status } from "../lib/signals";
import { displayPlace, displayTitle, distanceNote } from "../lib/curate";
import { eventPath, url } from "../lib/site";
import { dayKey, fmtDay, fmtTime, monthShort, parts, weekdayShort } from "../lib/time";
import type { Event } from "../lib/types";
import { Art } from "./Art";
import { Icon } from "./Icon";
import { WhyThis } from "./WhyThis";
import type { Scored } from "../lib/recommend";

/** A midnight start with no end is almost always a date-only listing, not a 12 AM event. */
export function isDateOnly(e: Event): boolean {
  const p = parts(e.start, e.timezone);
  return !!e.all_day || (p.hour === 0 && p.minute === 0 && !e.end);
}

export function eventHref(e: Event, city?: string): string {
  return url(eventPath(city ?? e.city, e.id, e.title));
}

export function Swatch({ category }: { category: string }) {
  return <span class="swatch" style={{ "--art-h": ART_HUE[familyOf(category)] }} aria-hidden="true" />;
}

export function StatusLine({ s, tag }: { s: Status | null; tag?: string | null }) {
  if (!s && !tag) return null;
  return (
    <p class="status">
      {s && (
        <span class={`status tone-${s.tone}`}>
          {s.icon && <Icon name={s.icon} size={14} />}
          {s.text}
        </span>
      )}
      {tag && <span class="tag">{s ? "· " : ""}{tag}</span>}
    </p>
  );
}

export function SaveButton({ e, label }: { e: Event; label?: boolean }) {
  const { saved, toggleSave } = useApp();
  const on = saved.includes(e.id);
  if (label) {
    return (
      <button class="btn btn-secondary btn-block" aria-pressed={on} onClick={() => toggleSave(e.id)}>
        <Icon name="bookmark" size={16} /> {on ? "Saved" : "Save"}
      </button>
    );
  }
  return (
    <button class="icon-btn save-btn" aria-pressed={on} aria-label={on ? `Remove ${e.title} from saved` : `Save ${e.title}`} title={on ? "Saved" : "Save"} onClick={() => toggleSave(e.id)}>
      <Icon name="bookmark" size={18} />
    </button>
  );
}

export function DateBox({ iso, tz, now, label }: { iso: string; tz: string; now: Date; label?: string }) {
  const p = parts(iso, tz);
  const today = dayKey(iso, tz) === dayKey(now, tz);
  const long = new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "long", month: "long", day: "numeric" }).format(new Date(iso));
  return (
    <time class={`datebox ${today && !label ? "today" : ""}`} dateTime={iso} aria-label={`${label ? `${label} ` : ""}${long}`}>
      <span class="m">{label ?? (today ? "Today" : monthShort(iso, tz))}</span>
      <span class="d">{p.day}</span>
      {!label && <span class="w">{weekdayShort(iso, tz)}</span>}
      {label && <span class="w">{monthShort(iso, tz).slice(0, 3)}</span>}
    </time>
  );
}

function TimeCell({ e }: { e: Event }) {
  if (e.kind === "opening") return <span class="erow-time soft">New</span>;
  if (isDateOnly(e)) return <span class="erow-time soft">All day</span>;
  const t = fmtTime(e.start, e.timezone);
  const [hm, ap] = t.split(" ");
  return (
    <time class="erow-time" dateTime={e.start}>
      {hm}
      <span class="ap">{ap}</span>
    </time>
  );
}

function metaLine(e: Event, price: string | null, more: number, cityName?: string, center?: [number, number]): ComponentChildren[] {
  const bits: ComponentChildren[] = [];
  const venue = displayPlace(e, cityName);
  if (venue) bits.push(venue);
  const far = distanceNote(e, center);
  if (far) bits.push(far);
  if (price) bits.push(price === "Free" ? <span class="free">Free</span> : price);
  if (more > 0) bits.push(`+${more} more date${more > 1 ? "s" : ""}`);
  else if (e.recurrence) bits.push(e.recurrence.replace(/\b(am|pm)\b/g, (m) => m.toUpperCase()));
  return bits.flatMap((b, i) => (i ? [" · ", b] : [b]));
}

/** List row: the default everywhere a list of events appears. `dated` shows the date block instead of the time. */
export function EventRow({ e, more = 0, dated = false, past = false, bare = false }: { e: Event; more?: number; dated?: boolean; past?: boolean; bare?: boolean }) {
  const { index, feed, now } = useApp();
  const sig = cardSignals(e, now);
  const hood = e.location.neighborhood;
  const id = `t-${e.id}`;
  const row = (
      <article class={`erow ${past ? "past" : ""}`} aria-labelledby={id} data-testid="event-card">
        {dated ? <DateBox iso={e.start} tz={e.timezone} now={now} /> : <TimeCell e={e} />}
        <div class="erow-body">
          <p class="erow-cat">
            <Swatch category={e.category} />
            <span>{catLabel(e.category, index.taxonomy)}{hood ? ` · ${hood}` : ""}{dated && !isDateOnly(e) && e.kind !== "opening" ? ` · ${fmtTime(e.start, e.timezone)}` : ""}</span>
          </p>
          <h3 class="erow-title" id={id}>
            <a href={eventHref(e, feed?.city)}>{displayTitle(e.title)}</a>
          </h3>
          <p class="erow-meta">{e.kind === "opening" ? <>New liquor or business license{e.location.address ? ` · ${displayPlace(e, feed?.city_name)}` : ""}</> : metaLine(e, sig.price, more, feed?.city_name, feed?.center as [number, number] | undefined)}</p>
          {past ? <p class="status tone-muted">Took place {fmtDay(e.start, e.timezone)}</p> : <StatusLine s={sig.status} tag={sig.tag} />}
        </div>
        <div class="erow-actions">
          <SaveButton e={e} />
        </div>
      </article>
  );
  return bare ? row : <li>{row}</li>;
}

/** Compact row: calendar agenda, map list, "similar", plan steps. */
export function CompactRow({ e, sub, time, onHover, hl }: { e: Event; sub?: string; time?: string; onHover?: (id: string | null) => void; hl?: boolean }) {
  const { feed, now } = useApp();
  const sig = cardSignals(e, now);
  const critical = sig.status?.tone === "critical";
  const ongoing = e.end && new Date(e.start) < now && new Date(e.end) > now;
  const t = time ?? (e.kind === "opening" ? "New" : ongoing ? "Ongoing" : isDateOnly(e) ? "All day" : fmtTime(e.start, e.timezone));
  return (
    <li class={`crow ${hl ? "hl" : ""} ${time === "" ? "nt" : ""}`} onMouseEnter={onHover && (() => onHover(e.id))} onMouseLeave={onHover && (() => onHover(null))} data-testid="event-card">
      {t !== "" && (
        <span class="t">
          {critical && <span class="dot-critical" title={sig.status!.text} />}
          {critical && <span class="sr-only">{sig.status!.text}. </span>}
          {t}
        </span>
      )}
      <span class="ti">
        <a href={eventHref(e, feed?.city)}>{displayTitle(e.title)}</a>
      </span>
      <span class="p">{sig.price === "Free" ? <span class="free">Free</span> : sig.price}</span>
      {sub && <span class="sub">{sub}</span>}
    </li>
  );
}

/** Featured card: at most 3–6 per page, with generated art. */
export function FeaturedCard({ e, why, scored }: { e: Event; why?: string; scored?: Scored }) {
  const { feed, now } = useApp();
  const sig = cardSignals(e, now);
  const tz = e.timezone;
  const when = `${dayKey(e.start, tz) === dayKey(now, tz) ? "Today" : fmtDay(e.start, tz)}${isDateOnly(e) ? "" : ` · ${fmtTime(e.start, tz)}`}`;
  const meta = [e.location.neighborhood ?? displayPlace(e, feed?.city_name), distanceNote(e, feed?.center as [number, number] | undefined), sig.price].filter(Boolean).join(" · ");
  return (
    <article class="fcard" data-testid="event-card">
      <Art id={e.id} family={familyOf(e.category)} ratio="2/1" />
      <SaveButton e={e} />
      <p class="eyebrow">{when}</p>
      <h3>
        <a href={eventHref(e, feed?.city)}>{displayTitle(e.title)}</a>
      </h3>
      {meta && <p class="meta">{meta}</p>}
      {why ? <p class="why">{why}</p> : sig.status && <StatusLine s={sig.status} />}
      {scored && <WhyThis s={scored} />}
    </article>
  );
}

export function SkeletonRows({ n = 6 }: { n?: number }) {
  return (
    <div aria-busy="true">
      <span class="sr-only">Loading events</span>
      {Array.from({ length: n }, (_, i) => (
        <div class="skel-row" key={i}>
          <div class="skel box" />
          <div class="bars">
            <div class="skel c" />
            <div class="skel t" />
            <div class="skel m" />
          </div>
        </div>
      ))}
    </div>
  );
}
