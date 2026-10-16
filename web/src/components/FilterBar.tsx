import { useApp } from "../lib/ctx";
import { catIcon, families, hue } from "../lib/categories";
import { DEFAULT_FILTERS, type Filters, SIZE_LABEL, type Size, type When, WHEN_LABEL } from "../lib/filters";
import { Icon } from "./Icon";

export function FilterBar({ resultCount }: { resultCount: number }) {
  const { index, route, go, feed } = useApp();
  const f = route.filters;
  const set = (patch: Partial<Filters>) => go({ filters: { ...f, ...patch } }, true);
  const fams = families(index.taxonomy);
  const toggleCat = (c: string) => set({ cats: f.cats.includes(c) ? f.cats.filter((x) => x !== c) : [...f.cats, c] });
  const active =
    f.cats.length + (f.free ? 1 : 0) + (f.social ? 1 : 0) + (f.size !== "any" ? 1 : 0) + (f.near ? 1 : 0) + (f.q ? 1 : 0) + (f.maxPrice != null ? 1 : 0);
  return (
    <section class="filters" aria-label="Filters">
      <div class="filter-row">
        <label class="search">
          <Icon name="search" size={16} />
          <input
            type="search"
            placeholder="Search trivia, kickball, ren faire…"
            value={f.q}
            onInput={(e) => set({ q: (e.target as HTMLInputElement).value })}
            aria-label="Search events"
          />
        </label>
        <div class="seg" role="radiogroup" aria-label="When">
          {(["today", "weekend", "week", "month", "all"] as When[]).map((w) => (
            <button key={w} role="radio" aria-checked={f.when === w} class={f.when === w ? "on" : ""} onClick={() => set({ when: w })}>
              {WHEN_LABEL[w]}
            </button>
          ))}
        </div>
      </div>
      <div class="chips scroll" role="group" aria-label="Categories">
        {fams.map((c) => (
          <button
            key={c}
            class={`chip cat-chip ${f.cats.includes(c) ? "on" : ""}`}
            style={{ "--h": hue(c) }}
            aria-pressed={f.cats.includes(c)}
            onClick={() => toggleCat(c)}
          >
            <Icon name={catIcon(c, index.taxonomy)} size={14} />
            {index.taxonomy[c].label}
          </button>
        ))}
      </div>
      <div class="filter-row toggles">
        <button class={`chip ${f.free ? "on" : ""}`} aria-pressed={f.free} onClick={() => set({ free: !f.free, maxPrice: null })}>
          Free only
        </button>
        <button class={`chip ${f.social ? "on" : ""}`} aria-pressed={f.social} onClick={() => set({ social: !f.social })} title="Social score ≥ 7/10">
          <Icon name="users" size={14} /> Good for meeting people
        </button>
        <label class="select">
          <span class="sr-only">Max price</span>
          <select
            value={f.maxPrice ?? ""}
            onChange={(e) => {
              const v = (e.target as HTMLSelectElement).value;
              set({ maxPrice: v ? Number(v) : null, free: false });
            }}
          >
            <option value="">Any price</option>
            <option value="15">Under $15</option>
            <option value="30">Under $30</option>
            <option value="60">Under $60</option>
            <option value="100">Under $100</option>
          </select>
        </label>
        <label class="select">
          <span class="sr-only">Crowd size</span>
          <select value={f.size} onChange={(e) => set({ size: (e.target as HTMLSelectElement).value as Size })}>
            {(Object.keys(SIZE_LABEL) as Size[]).map((s) => (
              <option key={s} value={s}>{SIZE_LABEL[s]}</option>
            ))}
          </select>
        </label>
        {!!feed?.neighborhoods?.length && (
          <label class="select">
            <span class="sr-only">Near</span>
            <select value={f.near ?? ""} onChange={(e) => set({ near: (e.target as HTMLSelectElement).value || null })}>
              <option value="">Anywhere in {feed.city_name}</option>
              {feed.neighborhoods.map((n) => (
                <option key={n.name} value={n.name}>Near {n.name}</option>
              ))}
            </select>
          </label>
        )}
        {f.near && (
          <label class="select">
            <span class="sr-only">Radius</span>
            <select value={f.radiusKm} onChange={(e) => set({ radiusKm: Number((e.target as HTMLSelectElement).value) })}>
              {[1, 2, 5, 10].map((r) => (
                <option key={r} value={r}>within {r} km</option>
              ))}
            </select>
          </label>
        )}
        <span class="result-count" aria-live="polite">
          {resultCount} {resultCount === 1 ? "thing" : "things"}
        </span>
        {active > 0 && (
          <button class="link" onClick={() => go({ filters: { ...DEFAULT_FILTERS, when: f.when } }, true)}>
            Clear {active}
          </button>
        )}
      </div>
    </section>
  );
}
