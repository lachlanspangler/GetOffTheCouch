// All event times render in the *city's* timezone, never the viewer's — a Minneapolis 7pm show is 7pm.

const cache = new Map<string, Intl.DateTimeFormat>();
function fmt(tz: string, opts: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = tz + JSON.stringify(opts);
  let f = cache.get(key);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", { timeZone: tz, ...opts });
    cache.set(key, f);
  }
  return f;
}

export interface LocalParts {
  year: number;
  month: number; // 1-12
  day: number;
  hour: number;
  minute: number;
  weekday: number; // 0=Sun
}

const WD: Record<string, number> = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

export function parts(iso: string | Date, tz: string): LocalParts {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const p = Object.fromEntries(
    fmt(tz, {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      weekday: "short",
      hourCycle: "h23",
    })
      .formatToParts(d)
      .map((x) => [x.type, x.value]),
  );
  return {
    year: +p.year,
    month: +p.month,
    day: +p.day,
    hour: +p.hour % 24,
    minute: +p.minute,
    weekday: WD[p.weekday] ?? 0,
  };
}

/** "2026-10-17" in the city's zone — the key for calendar days. */
export function dayKey(iso: string | Date, tz: string): string {
  const p = parts(iso, tz);
  return `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
}

export function fmtTime(iso: string, tz: string): string {
  return fmt(tz, { hour: "numeric", minute: "2-digit" }).format(new Date(iso)).replace(":00", "");
}

export function fmtDay(iso: string, tz: string): string {
  return fmt(tz, { weekday: "short", month: "short", day: "numeric" }).format(new Date(iso));
}

export function fmtDateLong(iso: string, tz: string): string {
  return fmt(tz, { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(new Date(iso));
}

export function monthShort(iso: string, tz: string): string {
  return fmt(tz, { month: "short" }).format(new Date(iso)).toUpperCase();
}

export function weekdayShort(iso: string, tz: string): string {
  return fmt(tz, { weekday: "short" }).format(new Date(iso));
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** "in 3 days", "tomorrow", "2 hours ago" */
export function relative(iso: string, now: Date = new Date()): string {
  const ms = new Date(iso).getTime() - now.getTime();
  const abs = Math.abs(ms);
  const min = 60_000, hr = 3_600_000, day = 86_400_000;
  if (abs < hr) return rtf.format(Math.round(ms / min), "minute");
  if (abs < day) return rtf.format(Math.round(ms / hr), "hour");
  if (abs < 30 * day) return rtf.format(Math.round(ms / day), "day");
  return rtf.format(Math.round(ms / (30 * day)), "month");
}

/** "checked 2h ago" — compact age for freshness labels. */
export function age(iso: string, now: Date = new Date()): string {
  const s = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (s < 90) return "just now";
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

export function hoursUntil(iso: string, now: Date = new Date()): number {
  return (new Date(iso).getTime() - now.getTime()) / 3_600_000;
}

export function isWeekend(iso: string, tz: string): boolean {
  const p = parts(iso, tz);
  return p.weekday === 0 || p.weekday === 6 || (p.weekday === 5 && p.hour >= 17);
}

/** "7–10 PM", "11 AM–2 PM", "7:30 PM" (en dash, no spaces; one meridiem when both ends share it). */
export function fmtTimeRange(start: string, end: string | null | undefined, tz: string): string {
  const a = fmtTime(start, tz);
  if (!end || dayKey(start, tz) !== dayKey(end, tz)) return a;
  const b = fmtTime(end, tz);
  if (a === b) return a;
  const ma = a.slice(-2), mb = b.slice(-2);
  return ma === mb ? `${a.slice(0, -3)}–${b}` : `${a}–${b}`;
}

/** Day group header: "Today · Fri, Oct 16", "Tomorrow · Sat, Oct 17", "Sun, Oct 18". */
export function dayHeader(key: string, tz: string, now: Date): { label: string; date: string } {
  const iso = `${key}T12:00:00Z`;
  const date = fmtDay(iso, "UTC");
  const today = dayKey(now, tz);
  const tomorrow = dayKey(new Date(now.getTime() + 86_400_000), tz);
  return { label: key === today ? "Today" : key === tomorrow ? "Tomorrow" : date, date: key === today || key === tomorrow ? date : "" };
}

/** "Fri, Oct 16 – Sun, Oct 18" for this weekend, in the city's zone. */
export function weekendRange(now: Date, tz: string): { from: Date; to: Date; label: string } {
  const p = parts(now, tz);
  const day = 86_400_000;
  const offFri = p.weekday === 0 ? -2 : p.weekday === 6 ? -1 : 5 - p.weekday;
  const from = new Date(now.getTime() + offFri * day);
  const to = new Date(from.getTime() + 2 * day);
  return { from, to, label: `${fmtDay(from.toISOString(), tz)} – ${fmtDay(to.toISOString(), tz)}` };
}

/** "CDT", "PST": the short zone name at that instant, so a timestamp is never ambiguous. */
export function tzAbbr(iso: string, tz: string): string {
  return fmt(tz, { timeZoneName: "short" }).formatToParts(new Date(iso)).find((p) => p.type === "timeZoneName")?.value ?? "";
}
