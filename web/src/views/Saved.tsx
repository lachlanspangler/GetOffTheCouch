import { useState } from "preact/hooks";
import { EventRow } from "../components/EventRow";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { calendar, download } from "../lib/ics";
import { share } from "./EventPage";
import { absolute } from "../lib/site";

export function Saved() {
  const { saved, byId, feed, route, go, toggleSave, now } = useApp();
  const [msg, setMsg] = useState<string | null>(null);
  if (!feed) return null;
  const shared = route.ids.length > 0;
  const ids = shared ? route.ids : saved;
  const events = ids.map((id) => byId.get(id)).filter((e) => e != null).sort((a, b) => a.start.localeCompare(b.start));
  const upcoming = events.filter((e) => new Date(e.end ?? e.start).getTime() >= now.getTime());
  const past = events.filter((e) => new Date(e.end ?? e.start).getTime() < now.getTime());
  const shareUrl = absolute(`${feed.city}/saved/?ids=${saved.join(",")}`);
  const gone = ids.length - events.length;
  return (
    <div class="container narrow">
      <header class="page-head inner">
        <h1>{shared ? "Shared with you" : "Saved"}</h1>
        <p class="lede">
          {shared ? "Someone shared these picks with you. Save the ones you like." : "Saved on this device only. Share a link to move them to another device."}
        </p>
        {events.length > 0 && (
          <div class="actions row">
            {shared ? (
              <>
                <button class="btn" onClick={() => events.forEach((e) => !saved.includes(e.id) && toggleSave(e.id))}>Save all {events.length}</button>
                <button class="btn btn-quiet" onClick={() => go({ ids: [] })}>Back to your saved</button>
              </>
            ) : (
              <button class="btn btn-secondary" onClick={async () => setMsg(await share(`My picks in ${feed.city_name}`, shareUrl))}>
                <Icon name="share" size={16} /> {msg ?? "Share list"}
              </button>
            )}
            <button class="btn btn-secondary" onClick={() => download(`${feed.city}-saved.ics`, calendar(upcoming, { name: `Saved in ${feed.city_name}` }))}>
              <Icon name="calendarPlus" size={16} /> Download calendar (.ics)
            </button>
          </div>
        )}
      </header>
      {events.length === 0 ? (
        <div class="empty">
          <h2>Nothing saved yet.</h2>
          <p>Tap Save on any event and it'll show up here, on this device only.</p>
        </div>
      ) : (
        <>
          {upcoming.length > 0 && (
            <section class="dl-group" aria-labelledby="up">
              <h2 id="up">Upcoming</h2>
              <ul class="rows">{upcoming.map((e) => <EventRow key={e.id} e={e} dated />)}</ul>
            </section>
          )}
          {past.length > 0 && (
            <section class="dl-group" aria-labelledby="pa">
              <h2 id="pa">Past</h2>
              <ul class="rows">{past.map((e) => <EventRow key={e.id} e={e} dated past />)}</ul>
            </section>
          )}
        </>
      )}
      {gone > 0 && <p class="small muted section">{gone} saved {gone === 1 ? "event is" : "events are"} no longer listed by the source.</p>}
    </div>
  );
}
