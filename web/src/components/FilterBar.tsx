// One-row filter bar with menus on desktop; search + "Filters (n)" + a When segment and a bottom sheet on
// mobile (DESIGN.md §4.4). Every filter lives in the URL.
import type { ComponentChildren } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { useApp } from "../lib/ctx";
import { children, families } from "../lib/categories";
import { DEFAULT_FILTERS, type Filters, SIZE_LABEL, type Size, type When, WHEN_LABEL } from "../lib/filters";
import { count } from "../lib/format";
import { ART_HUE, familyOf } from "../lib/art";
import { Icon } from "./Icon";

const TAG_FILTERS = ["solo_friendly", "beginner_friendly", "free_food", "accessible", "sober_friendly", "family_friendly", "dog_friendly", "lgbtq", "21+", "outdoor", "recurring", "registration_required"];
const WHENS: When[] = ["today", "tomorrow", "weekend", "week", "month", "all"];
const PRICES: { label: string; free: boolean; max: number | null }[] = [
  { label: "Any price", free: false, max: null },
  { label: "Free only", free: true, max: null },
  { label: "Under $20", free: false, max: 20 },
  { label: "Under $50", free: false, max: 50 },
];

function Menu({ label, active, children: body, wide, right }: { label: ComponentChildren; active?: boolean; children: (close: () => void) => ComponentChildren; wide?: string; right?: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setOpen(false); btn.current?.focus(); }
    };
    document.addEventListener("click", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("click", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);
  return (
    <div class="pop-anchor" ref={ref}>
      <button ref={btn} class={`fbtn ${active ? "active" : ""}`} aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}>
        {label} <Icon name="chevron" size={14} />
      </button>
      {open && <div class={`popover ${wide ?? ""} ${right ? "right" : ""}`}>{body(() => setOpen(false))}</div>}
    </div>
  );
}

function priceLabel(f: Filters): string {
  if (f.free) return "Free";
  if (f.maxPrice != null) return `Under $${f.maxPrice}`;
  return "Price";
}

export function activeCount(f: Filters): number {
  return f.cats.length + f.tags.length + (f.free ? 1 : 0) + (f.social ? 1 : 0) + (f.size !== "any" ? 1 : 0) + (f.near ? 1 : 0) + (f.maxPrice != null ? 1 : 0);
}

function SearchBox({ f, set }: { f: Filters; set: (p: Partial<Filters>) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState(f.q);
  useEffect(() => setQ(f.q), [f.q]);
  useEffect(() => {
    if (q === f.q) return;
    const t = setTimeout(() => set({ q }), 150);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") { e.preventDefault(); ref.current?.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  return (
    <label class="search">
      <Icon name="search" size={16} />
      <span class="sr-only">Search events</span>
      <input ref={ref} type="search" placeholder="Search events" value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />
      {q ? (
        <button class="icon-btn clear" aria-label="Clear search" onClick={() => { setQ(""); set({ q: "" }); }}>
          <Icon name="x" size={16} />
        </button>
      ) : (
        <kbd aria-hidden="true">/</kbd>
      )}
    </label>
  );
}

function CategoryChecks({ f, set, nested }: { f: Filters; set: (p: Partial<Filters>) => void; nested?: boolean }) {
  const { index } = useApp();
  const toggle = (c: string) => set({ cats: f.cats.includes(c) ? f.cats.filter((x) => x !== c) : [...f.cats, c] });
  return (
    <>
      {families(index.taxonomy).map((fam) => (
        <div key={fam}>
          <label class="check">
            <input type="checkbox" checked={f.cats.includes(fam)} onChange={() => toggle(fam)} />
            <span class="swatch" style={{ "--art-h": ART_HUE[familyOf(fam)] }} aria-hidden="true" />
            {index.taxonomy[fam].label}
          </label>
          {nested && (f.cats.includes(fam) || f.cats.some((c) => c.startsWith(`${fam}.`))) && (
            <div style={{ paddingLeft: "30px" }}>
              {children(index.taxonomy, fam).map((c) => (
                <label class="check" key={c}>
                  <input type="checkbox" checked={f.cats.includes(c) || f.cats.includes(fam)} disabled={f.cats.includes(fam)} onChange={() => toggle(c)} />
                  {index.taxonomy[c].label}
                </label>
              ))}
            </div>
          )}
        </div>
      ))}
    </>
  );
}

function MoreFields({ f, set }: { f: Filters; set: (p: Partial<Filters>) => void }) {
  const { index, feed } = useApp();
  return (
    <>
      <label class="check">
        <input type="checkbox" checked={f.social} onChange={() => set({ social: !f.social })} />
        Good for meeting people
      </label>
      <label class="field">
        <span class="label">Crowd size</span>
        <span class="select">
          <select value={f.size} onChange={(e) => set({ size: (e.target as HTMLSelectElement).value as Size })}>
            {(Object.keys(SIZE_LABEL) as Size[]).map((s) => <option key={s} value={s}>{SIZE_LABEL[s]}</option>)}
          </select>
        </span>
      </label>
      {!!feed?.neighborhoods?.length && (
        <label class="field">
          <span class="label">Neighborhood</span>
          <span class="select">
            <select value={f.near ?? ""} onChange={(e) => set({ near: (e.target as HTMLSelectElement).value || null })}>
              <option value="">Anywhere in {feed.city_name}</option>
              {feed.neighborhoods.map((n) => <option key={n.name} value={n.name}>Near {n.name}</option>)}
            </select>
          </span>
        </label>
      )}
      {f.near && (
        <label class="field">
          <span class="label">Distance</span>
          <span class="select">
            <select value={f.radiusKm} onChange={(e) => set({ radiusKm: Number((e.target as HTMLSelectElement).value) })}>
              {[1, 2, 5, 10].map((r) => <option key={r} value={r}>Within {r} km</option>)}
            </select>
          </span>
        </label>
      )}
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend class="label small" style={{ fontWeight: 500, marginBottom: "4px" }}>Good to know</legend>
        {TAG_FILTERS.map((t) => (
          <label class="check" key={t}>
            <input type="checkbox" checked={f.tags.includes(t)} onChange={() => set({ tags: f.tags.includes(t) ? f.tags.filter((x) => x !== t) : [...f.tags, t] })} />
            {index.tags[t] ?? t}
          </label>
        ))}
      </fieldset>
    </>
  );
}

function Applied({ f, set, clear }: { f: Filters; set: (p: Partial<Filters>) => void; clear: () => void }) {
  const { index } = useApp();
  const chips: { label: string; off: Partial<Filters> }[] = [
    ...f.cats.map((c) => ({ label: index.taxonomy[c]?.label ?? c, off: { cats: f.cats.filter((x) => x !== c) } })),
    ...(f.free ? [{ label: "Free only", off: { free: false } }] : []),
    ...(f.maxPrice != null ? [{ label: `Under $${f.maxPrice}`, off: { maxPrice: null } }] : []),
    ...(f.social ? [{ label: "Good for meeting people", off: { social: false } }] : []),
    ...(f.size !== "any" ? [{ label: SIZE_LABEL[f.size], off: { size: "any" as Size } }] : []),
    ...(f.near ? [{ label: `Near ${f.near}`, off: { near: null } }] : []),
    ...f.tags.map((t) => ({ label: index.tags[t] ?? t, off: { tags: f.tags.filter((x) => x !== t) } })),
  ];
  if (!chips.length) return null;
  return (
    <div class="applied">
      {chips.map((c) => (
        <button key={c.label} class="chip" aria-label={`Remove ${c.label}`} onClick={() => set(c.off)}>
          {c.label} <Icon name="x" size={14} />
        </button>
      ))}
      <button class="link-btn small" onClick={clear}>Clear all</button>
    </div>
  );
}

export function FilterBar({ resultCount, compact, noWhen }: { resultCount: number; compact?: boolean; noWhen?: boolean }) {
  const { index, route, go } = useApp();
  const f = route.filters;
  const set = (patch: Partial<Filters>) => go({ filters: { ...f, ...patch } }, true);
  const clear = () => go({ filters: { ...DEFAULT_FILTERS, when: f.when, q: f.q } }, true);
  const [sheet, setSheet] = useState(false);
  const n = activeCount(f);
  const catLabel = f.cats.length ? `${index.taxonomy[f.cats[0]]?.label ?? f.cats[0]}${f.cats.length > 1 ? ` + ${f.cats.length - 1}` : ""}` : "Category";
  const moreN = (f.social ? 1 : 0) + (f.size !== "any" ? 1 : 0) + (f.near ? 1 : 0) + f.tags.length;
  const results = `${count(resultCount)} ${resultCount === 1 ? "event" : "events"}`;
  return (
    <section aria-label="Filters">
      <div class="filterbar">
        <SearchBox f={f} set={set} />
        {!noWhen && <Menu label={f.when === DEFAULT_FILTERS.when ? "When" : WHEN_LABEL[f.when]} active={f.when !== DEFAULT_FILTERS.when}>
          {(close) => WHENS.map((w) => (
            <button key={w} class="menu-item" aria-pressed={f.when === w} onClick={() => { set({ when: w }); close(); }}>
              {WHEN_LABEL[w]}
              {f.when === w && <Icon name="check" size={16} class="tick" />}
            </button>
          ))}
        </Menu>}
        {!compact && (
          <Menu label={catLabel} active={f.cats.length > 0} wide="cat-menu">
            {() => <CategoryChecks f={f} set={set} />}
          </Menu>
        )}
        <Menu label={priceLabel(f)} active={f.free || f.maxPrice != null}>
          {(close) => PRICES.map((p) => {
            const on = f.free === p.free && f.maxPrice === p.max;
            return (
              <button key={p.label} class="menu-item" aria-pressed={on} onClick={() => { set({ free: p.free, maxPrice: p.max }); close(); }}>
                {p.label}
                {on && <Icon name="check" size={16} class="tick" />}
              </button>
            );
          })}
        </Menu>
        {!compact && (
          <Menu label={moreN ? `More filters (${moreN})` : "More filters"} active={moreN > 0} wide="more-menu" right>
            {() => <MoreFields f={f} set={set} />}
          </Menu>
        )}
        <span class="count" aria-live="polite">{results}</span>
      </div>
      <div class="filterbar-mobile">
        <div class="top">
          <SearchBox f={f} set={set} />
          <button class={`fbtn ${n ? "active" : ""}`} onClick={() => setSheet(true)} aria-haspopup="dialog">
            <Icon name="filter" size={16} /> Filters{n ? ` (${n})` : ""}
          </button>
        </div>
        {!noWhen && <div class="seg" role="radiogroup" aria-label="When">
          {(["today", "weekend", "week", "month"] as When[]).map((w) => (
            <button key={w} role="radio" aria-checked={f.when === w} onClick={() => set({ when: w })}>
              {{ today: "Today", weekend: "Weekend", week: "7 days", month: "30 days" }[w as "today"]}
            </button>
          ))}
        </div>}
      </div>
      <Applied f={f} set={set} clear={clear} />
      {sheet && <FilterSheet f={f} set={set} clear={clear} close={() => setSheet(false)} results={results} />}
    </section>
  );
}

function FilterSheet({ f, set, clear, close, results }: { f: Filters; set: (p: Partial<Filters>) => void; clear: () => void; close: () => void; results: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>("button, input")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab" && ref.current) {
        const els = [...ref.current.querySelectorAll<HTMLElement>("button, input, select, a[href]")].filter((x) => !x.hasAttribute("disabled"));
        if (!els.length) return;
        const first = els[0], last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; prev?.focus(); };
  }, []);
  return (
    <div class="sheet-wrap" onClick={(e) => e.target === e.currentTarget && close()}>
      <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" ref={ref}>
        <div class="sheet-handle" aria-hidden="true" />
        <div class="sheet-head">
          <h2 id="sheet-title">Filters</h2>
          <button class="icon-btn" onClick={close} aria-label="Close filters"><Icon name="x" /></button>
        </div>
        <div class="sheet-body">
          <section class="sheet-section">
            <h3>When</h3>
            {WHENS.map((w) => (
              <label class="check" key={w}>
                <input type="radio" name="when" checked={f.when === w} onChange={() => set({ when: w })} />
                {WHEN_LABEL[w]}
              </label>
            ))}
          </section>
          <section class="sheet-section">
            <h3>Category</h3>
            <CategoryChecks f={f} set={set} nested />
          </section>
          <section class="sheet-section">
            <h3>Price</h3>
            {PRICES.map((p) => (
              <label class="check" key={p.label}>
                <input type="radio" name="price" checked={f.free === p.free && f.maxPrice === p.max} onChange={() => set({ free: p.free, maxPrice: p.max })} />
                {p.label}
              </label>
            ))}
          </section>
          <section class="sheet-section">
            <h3>More</h3>
            <MoreFields f={f} set={set} />
          </section>
        </div>
        <div class="sheet-foot">
          <button class="btn btn-quiet" onClick={clear}>Clear all</button>
          <button class="btn btn-lg btn-primary-wide" onClick={close}>Show {results}</button>
        </div>
      </div>
    </div>
  );
}
