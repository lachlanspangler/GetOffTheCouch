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
