// City switcher (DESIGN.md §4.2): a quiet button that opens a searchable combobox.
// `hero` renders the always-visible search used on the home page.
import { useEffect, useRef, useState } from "preact/hooks";
import { useApp } from "../lib/ctx";
import { build } from "../lib/router";
import { count } from "../lib/format";
import type { CitySummary } from "../lib/types";
import { Icon } from "./Icon";

function useCityNav() {
  const { route, go } = useApp();
  return (c: CitySummary) => {
    // keep the filters that make sense in any city; drop neighborhood and tags
    const f = route.filters;
    go({ city: c.slug, eventId: null, view: route.city ? route.view : "feed", filters: { ...f, near: null, tags: [] }, day: null, ids: [] });
  };
}

function CityList({ q, active, onPick, listId }: { q: string; active: number; onPick: (c: CitySummary) => void; listId: string }) {
  const { index, route } = useApp();
  const list = filterCities(index.cities, q);
  return (
    <div class="city-list" role="listbox" id={listId} aria-label="Cities">
      {list.map((c, i) => (
        <button
          key={c.slug}
          id={`${listId}-${c.slug}`}
          role="option"
          aria-selected={c.slug === route.city}
          class={`city-opt ${i === active ? "active" : ""}`}
          tabIndex={-1}
          onClick={() => onPick(c)}
        >
          <span class="nm">{c.name}</span>
          <span class="st">{c.state}{c.slug === route.city && <Icon name="check" size={16} class="tick" />}</span>
          <span class="sub">{c.events ? `${count(c.upcoming_7d)} events this week · ${count(c.deadlines)} deadlines` : "Coming soon"}</span>
        </button>
      ))}
      {!list.length && <p class="muted small" style={{ padding: "10px" }}>No city by that name yet.</p>}
    </div>
  );
}

export function filterCities(cities: CitySummary[], q: string): CitySummary[] {
  const s = q.trim().toLowerCase();
  const sorted = [...cities].sort((a, b) => a.name.localeCompare(b.name));
  return s ? sorted.filter((c) => `${c.name} ${c.state}`.toLowerCase().includes(s)) : sorted;
}

function useCombo(onPick: (c: CitySummary) => void, close: () => void) {
  const { index } = useApp();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const list = filterCities(index.cities, q);
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(Math.min(list.length - 1, active + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(Math.max(0, active - 1)); }
    else if (e.key === "Enter" && list[active]) { e.preventDefault(); onPick(list[active]); }
    else if (e.key === "Escape") close();
  };
  return { q, setQ: (v: string) => { setQ(v); setActive(0); }, active, list, onKeyDown };
}

export function CityPicker() {
  const { index, route } = useApp();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const nav = useCityNav();
  const close = () => { setOpen(false); btn.current?.focus(); };
  const pick = (c: CitySummary) => { setOpen(false); nav(c); };
  const combo = useCombo(pick, close);
  const current = index.cities.find((c) => c.slug === route.city);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [open]);
  return (
    <div class="pop-anchor" ref={ref}>
      <button ref={btn} class="city-btn" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)} aria-label={current ? `City: ${current.name}. Change city` : "Choose a city"}>
        {current ? current.name : "Choose a city"}
        <Icon name="chevron" size={16} />
      </button>
      {open && (
        <div class="popover city-pop">
          <input
            class="input"
            role="combobox"
            aria-expanded="true"
            aria-controls="city-list-h"
            aria-activedescendant={combo.list[combo.active] ? `city-list-h-${combo.list[combo.active].slug}` : undefined}
            aria-label="Search cities"
            placeholder="Search cities"
            value={combo.q}
            autoFocus
            onInput={(e) => combo.setQ((e.target as HTMLInputElement).value)}
            onKeyDown={combo.onKeyDown}
          />
          <CityList q={combo.q} active={combo.active} onPick={pick} listId="city-list-h" />
        </div>
      )}
    </div>
  );
}

/** The home page's "Which city are you in?" search, with suggestions under it. */
export function CitySearch() {
  const [open, setOpen] = useState(false);
  const nav = useCityNav();
  const combo = useCombo(nav, () => setOpen(false));
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);
  return (
    <div class="pop-anchor" ref={ref}>
      <label class="search">
        <Icon name="search" size={16} />
        <span class="sr-only">Which city are you in?</span>
        <input
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls="city-list-home"
          aria-activedescendant={open && combo.list[combo.active] ? `city-list-home-${combo.list[combo.active].slug}` : undefined}
          placeholder="Which city are you in?"
          value={combo.q}
          onFocus={() => setOpen(true)}
          onInput={(e) => { combo.setQ((e.target as HTMLInputElement).value); setOpen(true); }}
          onKeyDown={combo.onKeyDown}
        />
      </label>
      {open && (
        <div class="popover city-pop" style={{ width: "100%" }}>
          <CityList q={combo.q} active={combo.active} onPick={nav} listId="city-list-home" />
        </div>
      )}
    </div>
  );
}

export function cityHref(slug: string): string {
  return build({ city: slug, view: "feed" });
}
