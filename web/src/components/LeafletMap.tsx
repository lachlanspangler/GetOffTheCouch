// Leaflet, lazy-loaded (it's the heaviest dependency; most visits never open a map).
// Tiles: OpenStreetMap standard tiles with attribution, per the OSMF tile usage policy (light use), calmed to
// grayscale in CSS. Pins are one ink color: category is a filter, not a legend (DESIGN.md §4.9).
import { useEffect, useRef } from "preact/hooks";
import type * as L from "leaflet";
import type { Map as LMap } from "leaflet";

export interface Pin {
  id: string;
  lat: number;
  lon: number;
  hue: number;
  title: string;
  sub: string;
  href?: string;
  approx?: boolean; // low-confidence location → hollow pin
}

function cssVar(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function LeafletMap({
  center,
  pins,
  zoom = 12,
  height,
  label = "Map",
  still = false,
  highlight = null,
}: {
  center: [number, number];
  pins: Pin[];
  zoom?: number;
  height?: string;
  label?: string;
  still?: boolean;
  highlight?: string | null;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<LMap | null>(null);
  const markers = useRef(new Map<string, L.CircleMarker>());
  useEffect(() => {
    let cancelled = false;
    let layer: { remove: () => void } | null = null;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");
      const cluster = pins.length > 150;
      if (cluster) {
        (window as unknown as { L: unknown }).L = L; // the plugin attaches to the global L
        await import("leaflet.markercluster");
        await import("leaflet.markercluster/dist/MarkerCluster.css");
      }
      if (cancelled || !el.current) return;
      if (!map.current) {
        const opts = still
          ? { zoomControl: false, dragging: false, scrollWheelZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false }
          : { zoomControl: true, scrollWheelZoom: false };
        map.current = L.map(el.current, { attributionControl: true, preferCanvas: true, ...opts }).setView(center, zoom);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map.current);
      }
      const ink = cssVar("--color-text", "#1F1D1A");
      const surface = cssVar("--color-surface", "#FFFFFF");
      const accent = cssVar("--color-accent", "#B8421F");
      const useCluster = cluster && typeof (L as unknown as { markerClusterGroup?: unknown }).markerClusterGroup === "function";
      const group: L.FeatureGroup = useCluster
        ? (L as unknown as { markerClusterGroup: (o: object) => L.FeatureGroup }).markerClusterGroup({
            showCoverageOnHover: false,
            maxClusterRadius: 45,
            iconCreateFunction: (c: { getChildCount: () => number }) => {
              const n = c.getChildCount();
              const s = n < 10 ? 28 : n < 100 ? 36 : 44;
              return L.divIcon({ html: `<span>${n}</span>`, className: "pin-cluster", iconSize: L.point(s, s) });
            },
          })
        : L.featureGroup();
      markers.current.clear();
      for (const p of pins) {
        const m = L.circleMarker([p.lat, p.lon], {
          radius: still ? 8 : 6,
          color: surface,
          weight: 2,
          fillColor: still ? accent : ink,
          fillOpacity: p.approx ? 0.35 : 1,
          dashArray: p.approx ? "3 3" : undefined,
        });
        if (!still) {
          const div = document.createElement("div");
          div.className = "map-pop";
          const b = document.createElement("strong");
          b.textContent = p.title;
          const s = document.createElement("div");
          s.textContent = p.sub;
          div.append(b, s);
          if (p.href) {
            const a = document.createElement("a");
            a.href = p.href;
            a.textContent = "View event";
            div.append(a);
          }
          m.bindPopup(div);
        }
        markers.current.set(p.id, m);
        group.addLayer(m);
      }
      group.addTo(map.current);
      layer = group;
      if (pins.length > 1) map.current.fitBounds(group.getBounds().pad(0.12), { maxZoom: 14 });
      else if (pins.length === 1) map.current.setView([pins[0].lat, pins[0].lon], zoom >= 14 ? zoom : 15);
    })();
    return () => {
      cancelled = true;
      layer?.remove();
    };
  }, [pins]);
  useEffect(() => {
    const ink = cssVar("--color-text", "#1F1D1A");
    const accent = cssVar("--color-accent", "#B8421F");
    for (const [id, m] of markers.current) {
      const on = id === highlight;
      m.setStyle({ fillColor: on ? accent : ink, radius: on ? 10 : 6 } as L.CircleMarkerOptions);
      if (on) m.bringToFront();
    }
  }, [highlight]);
  useEffect(() => () => { map.current?.remove(); map.current = null; }, []);
  return <div ref={el} class="leaflet-host" style={height ? { height } : undefined} role="region" aria-label={label} />;
}
