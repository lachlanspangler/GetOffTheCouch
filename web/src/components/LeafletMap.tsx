// Leaflet, lazy-loaded (it's the heaviest dependency; most visits never open the map).
// Tiles: OpenStreetMap standard tiles with attribution, per the OSMF tile usage policy (light use).
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
  approx?: boolean; // low-confidence location → hollow pin
}

export function LeafletMap({
  center,
  pins,
  zoom = 12,
  onPick,
  height,
  label = "Map",
}: {
  center: [number, number];
  pins: Pin[];
  zoom?: number;
  onPick?: (id: string) => void;
  height?: string;
  label?: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<LMap | null>(null);
  useEffect(() => {
    let cancelled = false;
    let layer: { remove: () => void } | null = null;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");
      if (pins.length > 150) {
        (window as unknown as { L: unknown }).L = L; // the plugin attaches to the global L
        await import("leaflet.markercluster");
        await import("leaflet.markercluster/dist/MarkerCluster.css");
      }
      if (cancelled || !el.current) return;
      if (!map.current) {
        map.current = L.map(el.current, { zoomControl: true, attributionControl: true, preferCanvas: true }).setView(center, zoom);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map.current);
      }
      const cluster = pins.length > 150 && typeof (L as unknown as { markerClusterGroup?: unknown }).markerClusterGroup === "function";
      const group: L.FeatureGroup = cluster
        ? (L as unknown as { markerClusterGroup: (o: object) => L.FeatureGroup }).markerClusterGroup({
            showCoverageOnHover: false,
            maxClusterRadius: 45,
            iconCreateFunction: (c: { getChildCount: () => number }) =>
              L.divIcon({ html: `<span>${c.getChildCount()}</span>`, className: "pin-cluster", iconSize: L.point(34, 34) }),
          })
        : L.featureGroup();
      for (const p of pins) {
        const m = L.circleMarker([p.lat, p.lon], {
          radius: 7,
          color: `hsl(${p.hue} 70% 35%)`,
          weight: 2,
          fillColor: `hsl(${p.hue} 80% 55%)`,
          fillOpacity: p.approx ? 0.15 : 0.85,
          dashArray: p.approx ? "3 3" : undefined,
        });
        const div = document.createElement("div");
        div.className = "map-pop";
        const b = document.createElement("strong");
        b.textContent = p.title;
        const s = document.createElement("div");
        s.textContent = p.sub;
        div.append(b, s);
        if (onPick) {
          const btn = document.createElement("button");
          btn.className = "btn btn-small";
          btn.textContent = "Details";
          btn.onclick = () => onPick(p.id);
          div.append(btn);
        }
        m.bindPopup(div);
        group.addLayer(m);
      }
      group.addTo(map.current);
      layer = group;
      if (pins.length > 1) map.current.fitBounds(group.getBounds().pad(0.15), { maxZoom: 14 });
      else if (pins.length === 1) map.current.setView([pins[0].lat, pins[0].lon], 15);
    })();
    return () => {
      cancelled = true;
      layer?.remove();
    };
  }, [pins]);
  useEffect(() => () => { map.current?.remove(); map.current = null; }, []);
  return <div ref={el} class="leaflet-host" style={height ? { height } : undefined} role="region" aria-label={label} />;
}
