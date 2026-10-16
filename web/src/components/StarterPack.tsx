// Official new-resident deadlines (license, vehicle, voting) with personal due dates from your move date.
import { useApp } from "../lib/ctx";
import { download } from "../lib/ics";
import type { Profile } from "../lib/recommend";
import { usePersistent } from "../lib/store";
import { fmtDay, relative } from "../lib/time";
import type { StarterItem } from "../lib/feed.generated";
import { Icon } from "./Icon";

const KIND_ICON: Record<string, string> = { license: "ticket", vehicle: "map", voting: "check", id: "ticket", inspection: "activity", other: "info" };

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
  const items = feed?.starter_pack ?? [];
  if (!feed || !items.length) return null;
  const move = profile?.startDate ? new Date(`${profile.startDate}T12:00:00`) : null;
  const ref = move ?? now;
  const sorted = [...items].sort((a, b) => (a.days_after_move ?? 9999) - (b.days_after_move ?? 9999));
  return (
    <section class="plan-block starter">
      <h3>
        <Icon name="check" size={18} /> New-resident to-dos for {feed.state}
      </h3>
      <p class="muted small">
        From official state websites, quoted and re-checked daily.{" "}
        {move ? (
          <>Due dates count from your move date, {fmtDay(move.toISOString(), feed.timezone)}.</>
        ) : (
          <>
            When did you (or will you) move?{" "}
            <input
              type="date"
              aria-label="Move date"
              onInput={(e) => {
                const v = (e.target as HTMLInputElement).value;
                if (v) setProfile({ ...(profile ?? { interests: [], goals: ["meet_people"], budget: "any", times: ["weeknights", "weekends"], neighborhood: null, solo: true }), startDate: v });
              }}
            />
          </>
        )}
      </p>
      <ul class="starter-list">
        {sorted.map((it) => {
          const due = dueDate(it, ref);
          const overdue = due && due < now;
          return (
            <li key={it.id} class={`starter-item ${overdue ? "overdue" : ""}`}>
              <Icon name={KIND_ICON[it.kind] ?? "info"} size={18} />
              <div>
                <a href={it.action_url} target="_blank" rel="noopener noreferrer"><strong>{it.title}</strong></a>
                <p class="small">{it.summary}</p>
                <p class="muted small">
                  {due ? (
                    <>Due {fmtDay(due.toISOString(), feed.timezone)} ({it.days_after_move} days after moving){move ? `, ${relative(due.toISOString(), now)}` : ""} · </>
                  ) : null}
                  <a href={it.source_url} target="_blank" rel="noopener noreferrer">source</a>
                  {it.check_status === "page_changed" && <span class="badge badge-stale">page changed: double-check</span>}
                  {it.check_status === "evidence_present" && it.last_checked && <> · re-checked {relative(it.last_checked, now)}</>}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
      {move && sorted.some((i) => i.days_after_move != null) && (
        <button class="btn btn-ghost" onClick={() => download(`${feed.city}-new-resident-deadlines.ics`, icsFor(sorted, move, feed.city_name))}>
          <Icon name="bell" size={16} /> Add these deadlines to my calendar
        </button>
      )}
    </section>
  );
}
