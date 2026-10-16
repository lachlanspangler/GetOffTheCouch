import { EventCard } from "../components/EventCard";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { calendar, download } from "../lib/ics";

export function Saved() {
  const { saved, byId, feed } = useApp();
  if (!feed) return null;
  const events = saved.map((id) => byId.get(id)).filter((e) => e != null).sort((a, b) => a.start.localeCompare(b.start));
  const gone = saved.length - events.length;
  return (
    <div>
      <header class="view-head">
        <div>
          <h2>Saved</h2>
          <p class="muted">Saved on this device only. We don't have accounts and don't track you.</p>
        </div>
        {events.length > 0 && (
          <button class="btn" onClick={() => download(`${feed.city}-saved.ics`, calendar(events, { name: "GetOffTheCouch — saved" }))}>
            <Icon name="calendar" size={16} /> Export {events.length} to calendar
          </button>
        )}
      </header>
      {events.length ? (
        <div class="grid">{events.map((e) => <EventCard key={e.id} e={e} />)}</div>
      ) : (
        <div class="empty">
          <Icon name="bookmark" size={36} />
          <h3>Nothing saved in {feed.city_name} yet</h3>
          <p class="muted">Tap the bookmark on anything that looks good.</p>
        </div>
      )}
      {gone > 0 && <p class="muted small">{gone} saved item(s) have passed or are no longer listed.</p>}
    </div>
  );
}
