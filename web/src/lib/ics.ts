// iCalendar export (RFC 5545) with alarms, so "remind me before registration closes" works in any
// calendar app without us running a server.
import type { Event } from "./types";

function stamp(iso: string | Date): string {
  return new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

function esc(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
}

/** Fold lines at 75 octets as RFC 5545 requires (approximated by characters). */
function fold(line: string): string {
  if (line.length <= 74) return line;
  const out: string[] = [];
  for (let i = 0; i < line.length; i += 73) out.push((i ? " " : "") + line.slice(i, i + 73));
  return out.join("\r\n");
}

function alarm(trigger: string, text: string): string[] {
  return ["BEGIN:VALARM", "ACTION:DISPLAY", `TRIGGER:${trigger}`, `DESCRIPTION:${esc(text)}`, "END:VALARM"];
}

export function veventFor(e: Event, now: Date = new Date()): string[] {
  const lines = [
    "BEGIN:VEVENT",
    `UID:${e.id}@getoffthecouch`,
    `DTSTAMP:${stamp(now)}`,
  ];
  if (e.all_day) {
    const d = e.start.slice(0, 10).replace(/-/g, "");
    lines.push(`DTSTART;VALUE=DATE:${d}`);
  } else {
    lines.push(`DTSTART:${stamp(e.start)}`);
    const end = e.end ?? new Date(new Date(e.start).getTime() + 2 * 3600_000).toISOString();
    lines.push(`DTEND:${stamp(end)}`);
  }
  lines.push(`SUMMARY:${esc(e.title)}`);
  const loc = [e.location.venue_name, e.location.address].filter(Boolean).join(", ");
  if (loc) lines.push(`LOCATION:${esc(loc)}`);
  if (e.location.lat != null && e.location.lon != null) lines.push(`GEO:${e.location.lat};${e.location.lon}`);
  const url = e.offers?.[0]?.url ?? e.url;
  if (url) lines.push(`URL:${url}`);
  const desc = [e.summary ?? "", url ? `\n${url}` : "", "\n— via GetOffTheCouch"].join("");
  lines.push(`DESCRIPTION:${esc(desc.trim())}`);
  lines.push(...alarm("-PT2H", `${e.title} starts in 2 hours`));
  lines.push("END:VEVENT");
  return lines;
}

/** A separate all-day-ish item on the deadline itself, with reminders 2 days and 3 hours before. */
export function vdeadlineFor(e: Event, now: Date = new Date()): string[] {
  const at = e.registration?.closes_at;
  if (!at) return [];
  const url = e.registration?.url ?? e.offers?.find((o) => o.kind === "registration")?.url ?? e.url;
  return [
    "BEGIN:VEVENT",
    `UID:${e.id}-deadline@getoffthecouch`,
    `DTSTAMP:${stamp(now)}`,
    `DTSTART:${stamp(new Date(new Date(at).getTime() - 30 * 60_000))}`,
    `DTEND:${stamp(at)}`,
    `SUMMARY:${esc(`⏰ Register: ${e.title}`)}`,
    ...(url ? [`URL:${url}`] : []),
    `DESCRIPTION:${esc(`Registration closes for ${e.title}.${url ? `\n${url}` : ""}${e.registration?.evidence ? `\n“${e.registration.evidence}”` : ""}`)}`,
    ...alarm("-P2D", `Registration for ${e.title} closes in 2 days`),
    ...alarm("-PT3H", `Registration for ${e.title} closes in 3 hours`),
    "END:VEVENT",
  ];
}

export function calendar(
  events: Event[],
  opts: { mode?: "events" | "deadlines" | "both"; name?: string } = {},
): string {
  const now = new Date();
  const mode = opts.mode ?? "both";
  const body: string[] = [];
  for (const e of events) {
    if (mode !== "deadlines") body.push(...veventFor(e, now));
    if (mode !== "events") body.push(...vdeadlineFor(e, now));
  }
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//GetOffTheCouch//ur city made easy//EN",
    "CALSCALE:GREGORIAN",
    `X-WR-CALNAME:${esc(opts.name ?? "GetOffTheCouch")}`,
    ...body,
    "END:VCALENDAR",
  ]
    .map(fold)
    .join("\r\n") + "\r\n";
}

export function download(filename: string, text: string, type = "text/calendar"): void {
  const blob = new Blob([text], { type });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(a.href);
    a.remove();
  }, 0);
}

export function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "event";
}
