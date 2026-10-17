// List + map split (DESIGN.md §4.9). The list is the accessible equivalent of the map.
import { useMemo, useState } from "preact/hooks";
import { CompactRow, eventHref } from "../components/EventRow";
import { FilterBar } from "../components/FilterBar";
import { LeafletMap, type Pin } from "../components/LeafletMap";
import { useApp } from "../lib/ctx";
import { collapseSeries } from "../lib/filters";
import { count } from "../lib/format";
import { displayPlace, displayTitle, isLeadable, isUnderway } from "../lib/curate";
import { fmtDay, fmtTime } from "../lib/time";
import type { Event } from "../lib/types";

export function MapView({ events }: { events: Event[] }) {
  const { feed, now } = useApp();
  const [hl, setHl] = useState<string | null>(null);
  const items = useMemo(() => collapseSeries(events.filter((e) => e.kind !== "opening" && isLeadable(e, feed?.state) && !isUnderway(e, now))).map((g) => g.event), [events, now]);
  const pins = useMemo<Pin[]>(
    () =>
      items
        .filter((e) => e.location.lat != null && e.location.lon != null)
        .map((e) => ({
          id: e.id,
          lat: e.location.lat as number,
          lon: e.location.lon as number,
          hue: 0,
          title: displayTitle(e.title),
          href: eventHref(e, feed?.city),
          approx: (e.location.geocode_confidence ?? 1) < 0.5,
          sub: `${e.kind === "opening" ? "New license" : `${fmtDay(e.start, e.timezone)} · ${fmtTime(e.start, e.timezone)}`}${e.location.venue_name ? ` · ${e.location.venue_name}` : ""}`,
        })),
    [items],
  );
  if (!feed) return null;
  const missing = items.length - pins.length;
  const mapped = new Set(pins.map((p) => p.id));
  const listed = items.filter((e) => mapped.has(e.id)).slice(0, 200);
  return (
    <div class="container">
      <header class="page-head inner">
        <h1>Map</h1>
        <p class="lede">Where things are happening in {feed.city_name}.</p>
      </header>
      <FilterBar resultCount={events.length} />
      <div class="map-split">
        <div class="map-list">
          <p class="small muted">
            {count(pins.length)} on the map{missing > 0 ? ` · ${count(missing)} without a mappable address` : ""}
            {pins.some((p) => p.approx) && " · faded pins are approximate"}
          </p>
          <ul class="rows">
            {listed.map((e) => (
              <CompactRow key={e.id} e={e} hl={hl === e.id} onHover={setHl} time={new Date(e.start) < now ? "Ongoing" : fmtDay(e.start, e.timezone)} sub={displayPlace(e, feed.city_name) ?? undefined} />
            ))}
          </ul>
          {items.length > listed.length && <p class="small muted" style={{ marginTop: "8px" }}>Showing the first {listed.length}. Narrow the filters to see the rest.</p>}
        </div>
        <div class="map-pane">
          <LeafletMap
            center={feed.center as [number, number]}
            zoom={12}
            fit={pins.length <= 40}
            pins={pins}
            highlight={hl}
            label={`Map of ${count(pins.length)} events in ${feed.city_name}. The list has the same events.`}
          />
        </div>
      </div>
    </div>
  );
}
