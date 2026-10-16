// Official new-resident deadlines (license, vehicle, voting) with personal due dates from your move date.
import { useApp } from "../lib/ctx";
import { download } from "../lib/ics";
import { stateName } from "../lib/format";
import type { Profile } from "../lib/recommend";
import { usePersistent } from "../lib/store";
import { fmtDay, relative } from "../lib/time";
import type { StarterItem } from "../lib/feed.generated";
import { Icon } from "./Icon";

export function dueDate(item: StarterItem, moveDate: Date): Date | null {
  return item.days_after_move == null ? null : new Date(moveDate.getTime() + item.days_after_move * 86_400_000);
}

function icsFor(items: StarterItem[], move: Date, city: string): string {
  const stamp = (d: Date) => d.toISOString().slice(0, 10).replace(/-/g, "");
  const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
  const body = items.flatMap((it) => {
    const due = dueDate(it, move);
    if (!due) return [];
    return [
      "BEGIN:VEVENT",
      `UID:${it.id}-${stamp(move)}@getoffthecouch`,
      `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "")}`,
      `DTSTART;VALUE=DATE:${stamp(due)}`,
      `SUMMARY:${esc(`Deadline: ${it.title}`)}`,
      `URL:${it.action_url}`,
      `DESCRIPTION:${esc(`${it.summary}\n${it.action_url}\nSource: ${it.source_url}`)}`,
      "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P14D", `DESCRIPTION:${esc(`${it.title}: 2 weeks left`)}`, "END:VALARM",
      "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P2D", `DESCRIPTION:${esc(`${it.title}: 2 days left`)}`, "END:VALARM",
      "END:VEVENT",
    ];
  });
  return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//GetOffTheCouch//EN", `X-WR-CALNAME:New in ${city}`, ...body, "END:VCALENDAR"].join("\r\n") + "\r\n";
}

export function StarterPack() {
  const { feed, now } = useApp();
  const [profile, setProfile] = usePersistent<Profile | null>(`profile:${feed?.city ?? "_"}`, null);
  const [done, setDone] = usePersistent<string[]>(`todos:${feed?.city ?? "_"}`, []);
  const items = feed?.starter_pack ?? [];
  if (!feed || !items.length) return null;
  const move = profile?.startDate ? new Date(`${profile.startDate}T12:00:00`) : null;
  const sorted = [...items].sort((a, b) => (a.days_after_move ?? 9999) - (b.days_after_move ?? 9999));
  const setMove = (v: string) =>
    setProfile({ ...(profile ?? { interests: [], goals: ["meet_people"], budget: "any", times: ["weeknights", "weekends"], neighborhood: null, solo: true }), startDate: v || null });
  return (
    <section class="todo-card" aria-labelledby="todo-h">
      <h2 id="todo-h">Moving to {stateName(feed.state)}: official deadlines</h2>
      <p>License, registration and voter paperwork, from official state websites, re-checked daily.</p>
      <label class="field">
        <span class="label">When did you move (or when will you)?</span>
        <input class="input" type="date" value={profile?.startDate ?? ""} onInput={(e) => setMove((e.target as HTMLInputElement).value)} aria-describedby="move-help" />
        <span class="help" id="move-help">We use this to work out your due dates. It stays on this device.</span>
      </label>
      <ul class="todo-list">
        {sorted.map((it) => {
          const due = move ? dueDate(it, move) : null;
          const overdue = due && due < now;
          const isDone = done.includes(it.id);
          return (
            <li key={it.id} class={`todo ${isDone ? "done" : ""}`}>
              <input type="checkbox" checked={isDone} aria-label={`Mark "${it.title}" done`} onChange={() => setDone(isDone ? done.filter((x) => x !== it.id) : [...done, it.id])} />
              <div>
                <p class="title">{it.title}</p>
                <p class="sum">{it.summary}</p>
                <p class="sum">
                  {due ? (
                    <span class={overdue && !isDone ? "tone-critical" : ""}>
                      Due {fmtDay(due.toISOString(), feed.timezone)} · {it.days_after_move} days after your move{overdue && !isDone ? " (past due)" : ""}
                    </span>
                  ) : it.days_after_move != null ? (
                    <>Due {it.days_after_move} days after you move</>
                  ) : null}
                  {(due || it.days_after_move != null) && " · "}
                  <a href={it.action_url} target="_blank" rel="noopener noreferrer">Official page ↗</a>
                </p>
                <p class="src">
                  Source: {host(it.source_url)}
                  {it.check_status === "evidence_present" && it.last_checked && <> · checked {relative(it.last_checked, now)}</>}
                  {it.check_status === "page_changed" && <span class="tone-caution"> · the official page changed recently, so double-check</span>}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
      {move && sorted.some((i) => i.days_after_move != null) && (
        <button class="btn btn-secondary" style={{ marginTop: "16px" }} onClick={() => download(`${feed.city}-new-resident-deadlines.ics`, icsFor(sorted, move, feed.city_name))}>
          <Icon name="calendarPlus" size={16} /> Add these to your calendar
        </button>
      )}
    </section>
  );
}

function host(u: string): string {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return u;
  }
}
