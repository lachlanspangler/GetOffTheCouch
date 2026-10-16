// Inline SVG icons (Lucide-style strokes, hand-trimmed). No icon font, no network.
import type { JSX } from "preact";

const P: Record<string, string> = {
  music: "M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  trophy: "M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4ZM7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4",
  sparkles: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3ZM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z",
  users: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  utensils: "M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2M7 2v20M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7",
  heart: "M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z",
  wand: "M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8 19 13M17.8 6.2 19 5M3 21l9-9M12.2 6.2 11 5",
  brain: "M12 5a3 3 0 1 0-5.9.9A4 4 0 0 0 4 13a4 4 0 0 0 6 3.5V5Zm0 0a3 3 0 1 1 5.9.9A4 4 0 0 1 20 13a4 4 0 0 1-6 3.5M12 5v14",
  run: "M13 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM4 22l4-7 3 2v5M15 22l-2-6-4-3 1-5 4 3h4M6 12l2-4h5",
  tree: "M12 22v-7M8 15h8l-3-4h2l-3-4h1.5L12 3 10.5 7H12L9 11h2l-3 4Z",
  palette: "M12 22a10 10 0 1 1 10-10c0 2.8-2.2 3-4 3h-2a2 2 0 0 0-1.5 3.3c.4.5.5 1 .5 1.5 0 1.2-1.3 2.2-3 2.2ZM7.5 10.5h.01M12 7.5h.01M16.5 10.5h.01",
  stadium: "M2 9c0-2.2 4.5-4 10-4s10 1.8 10 4v6c0 2.2-4.5 4-10 4S2 17.2 2 15V9Zm0 0c0 2.2 4.5 4 10 4s10-1.8 10-4M7 12.5v6M17 12.5v6M12 13v6",
  balloon: "M12 16c3.3 0 6-3 6-7A6 6 0 0 0 6 9c0 4 2.7 7 6 7Zm0 0-1 2h2l-1-2Zm0 2c0 2-2 2-2 4",
  book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15Zm0 0A2.5 2.5 0 0 0 6.5 22H20v-5",
  dot: "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z",
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z",
  map: "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Zm0 0v14m6-12v14",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-16v6l4 2",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm10 2-4.3-4.3",
  bookmark: "M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z",
  share: "M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  alert: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01",
  check: "M20 6 9 17l-5-5",
  x: "M18 6 6 18M6 6l12 12",
  chevron: "m6 9 6 6 6-6",
  left: "m15 18-6-6 6-6",
  right: "m9 18 6-6-6-6",
  pin: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Zm-8 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  ticket: "M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2Zm11-4v2m0 10v2m0-8v2",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  compass: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm4.2-14.2-2.1 6.3-6.3 2.1 2.1-6.3 6.3-2.1Z",
  filter: "M22 3H2l8 9.5V19l4 2v-8.5L22 3Z",
  external: "M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-6v-4m0-4h.01",
  flame: "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3.3.4 1.4 1.4 2.8 2.5 2.8Z",
  sofa: "M20 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v3M2 11a2 2 0 1 1 4 0v3h12v-3a2 2 0 1 1 4 0v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6Zm2 8v2m16-2v2",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10ZM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z",
  store: "M3 9 4.5 4h15L21 9M3 9v11h18V9M3 9h18M9 20v-6h6v6",
  menu: "M4 6h16M4 12h16M4 18h16",
  door: "M6 21V8a6 6 0 0 1 12 0v13M3 21h18",
  arrowLeft: "M19 12H5m7 7-7-7 7-7",
  calendarPlus: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM12 13v5M9.5 15.5h5",
  flag: "M4 22V4m0 0s1.5-1 4-1 4 2 6.5 2S18 4 18 4v10s-1.5 1-3.5 1-4-2-6.5-2-4 1-4 1",
  bell: "M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9ZM10.3 21a1.9 1.9 0 0 0 3.4 0",
};

export function Icon({ name, size = 18, class: cls, title }: { name: string; size?: number; class?: string; title?: string }): JSX.Element {
  return (
    <svg
      class={`icon ${cls ?? ""}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden={title ? undefined : "true"}
      role={title ? "img" : undefined}
    >
      {title ? <title>{title}</title> : null}
      <path d={P[name] ?? P.dot} />
    </svg>
  );
}
