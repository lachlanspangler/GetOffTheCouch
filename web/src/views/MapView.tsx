import { useMemo } from "preact/hooks";
import { LeafletMap, type Pin } from "../components/LeafletMap";
import { useApp } from "../lib/ctx";
import { hue } from "../lib/categories";
import { collapseSeries } from "../lib/filters";
import { fmtDay, fmtTime } from "../lib/time";
import type { Event } from "../lib/types";

export function MapView({ events }: { events: Event[] }) {
  const { feed, go } = useApp();
  const pins = useMemo<Pin[]>(
    () =>
      collapseSeries(events)
        .map((g) => g.event)
        .filter((e) => e.location.lat != null && e.location.lon != null)
        .map((e) => ({
          id: e.id,
          lat: e.location.lat as number,
          lon: e.location.lon as number,
          hue: hue(e.category),
          title: e.title,
          approx: (e.location.geocode_confidence ?? 1) < 0.5,
          sub: `${e.kind === "opening" ? "New spot" : `${fmtDay(e.start, e.timezone)} · ${fmtTime(e.start, e.timezone)}`} · ${e.location.venue_name ?? ""}`,
        })),
    [events],
  );
  if (!feed) return null;
  const missing = events.length - pins.length;
  return (
    <div class="map-view">
      <LeafletMap center={feed.center as [number, number]} pins={pins} onPick={(id) => go({ city: feed.city, eventId: id })} label={`Map of ${feed.city_name} events`} />
      <p class="muted small map-note">
        {pins.length} on the map{missing > 0 ? ` · ${missing} without a mappable address (see the list)` : ""}
        {pins.some((p) => p.approx) && " · hollow pins are approximate (e.g. somewhere on a campus)"}
      </p>
    </div>
  );
}
