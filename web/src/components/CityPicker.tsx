import { useEffect, useRef, useState } from "preact/hooks";
import { useApp } from "../lib/ctx";
import { Icon } from "./Icon";

export function CityPicker() {
  const { index, route, go } = useApp();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const current = index.cities.find((c) => c.slug === route.city);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => open && ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [open]);
  const list = index.cities.filter((c) => `${c.name} ${c.state}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div class="city-picker" ref={ref}>
      <button class="city-btn" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Icon name="pin" size={16} />
        <span>{current ? `${current.name}, ${current.state}` : "Pick your city"}</span>
        <Icon name="chevron" size={16} />
      </button>
      {open && (
        <div class="popover" role="listbox" aria-label="Cities">
          <input
            class="pop-search"
            placeholder="Search cities"
            value={q}
            autoFocus
            onInput={(e) => setQ((e.target as HTMLInputElement).value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && list[0]) {
                go({ city: list[0].slug, view: route.view === "about" ? "feed" : route.view, eventId: null });
                setOpen(false);
              }
              if (e.key === "Escape") setOpen(false);
            }}
          />
          {list.map((c) => (
            <button
              key={c.slug}
              role="option"
              aria-selected={c.slug === route.city}
              class={`pop-item ${c.slug === route.city ? "on" : ""}`}
              onClick={() => {
                go({ city: c.slug, eventId: null, view: route.view === "about" ? "feed" : route.view });
                setOpen(false);
              }}
            >
              <span>
                <strong>{c.name}</strong>, {c.state}
              </span>
              <span class="muted small">{c.events ? `${c.events} things · ${c.deadlines} deadlines` : "sources coming soon"}</span>
            </button>
          ))}
          <p class="muted small pad">USA only for now. Adding a city is a config file. Ask for yours!</p>
        </div>
      )}
    </div>
  );
}
