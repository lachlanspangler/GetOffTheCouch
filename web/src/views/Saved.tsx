import { EventCard } from "../components/EventCard";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { calendar, download } from "../lib/ics";
import { share } from "../components/EventDrawer";

export function Saved() {
  const { saved, byId, feed, route, go, toggleSave } = useApp();
  if (!feed) return null;
  const shared = route.ids.length > 0;
  const ids = shared ? route.ids : saved;
  const events = ids.map((id) => byId.get(id)).filter((e) => e != null).sort((a, b) => a.start.localeCompare(b.start));
  const shareUrl = `${location.origin}${location.pathname}#/${feed.city}/saved?ids=${saved.join(",")}`;
  const gone = saved.length - events.length;
  return (
    <div>
      <header class="view-head">
        <div>
          <h2>{shared ? "Shared with you" : "Saved"}</h2>
          <p class="muted">
            {shared
              ? "Someone shared these picks with you. Save the ones you like."
              : "Saved on this device only. We don't have accounts and don't track you."}
          </p>
        </div>
        {shared && events.length > 0 && (
          <div class="row">
            <button class="btn" onClick={() => events.forEach((e) => !saved.includes(e.id) && toggleSave(e.id))}>Save all {events.length}</button>
            <button class="btn btn-ghost" onClick={() => go({ ids: [] })}>Back to my saved</button>
          </div>
        )}
        {!shared && events.length > 0 && (
          <button class="btn btn-ghost" onClick={async (ev) => { const t = ev.currentTarget; t.textContent = await share("My GetOffTheCouch picks", shareUrl); }}>
            <Icon name="share" size={16} /> Share list
          </button>
        )}
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
