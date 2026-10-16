import { useEffect, useMemo, useState } from "preact/hooks";
import { CityPicker } from "./components/CityPicker";
import { EventDrawer } from "./components/EventDrawer";
import { FilterBar } from "./components/FilterBar";
import { Icon } from "./components/Icon";
import { Ctx, type AppCtx } from "./lib/ctx";
import { isDemo, loadCity, loadIndex } from "./lib/data";
import { applyFilters, deadlines } from "./lib/filters";
import { build, setTitleLookup, useRoute, type View } from "./lib/router";
import { url } from "./lib/site";
import { usePersistent } from "./lib/store";
import { age } from "./lib/time";
import type { CityFeed, Index } from "./lib/types";
import { About } from "./views/About";
import { Calendar } from "./views/Calendar";
import { Deadlines } from "./views/Deadlines";
import { Feed } from "./views/Feed";
import { Health } from "./views/Health";
import { Home } from "./views/Home";
import { MapView } from "./views/MapView";
import { Plan } from "./views/Plan";
import { Saved } from "./views/Saved";

const TABS: { view: View; label: string; icon: string }[] = [
  { view: "feed", label: "Feed", icon: "list" },
  { view: "deadlines", label: "Deadlines", icon: "clock" },
  { view: "calendar", label: "Calendar", icon: "calendar" },
  { view: "map", label: "Map", icon: "map" },
  { view: "plan", label: "New in town", icon: "compass" },
  { view: "saved", label: "Saved", icon: "bookmark" },
  { view: "health", label: "Health", icon: "activity" },
];

const FILTERED_VIEWS: View[] = ["feed", "calendar", "map"];

export function App() {
  const [route, go] = useRoute();
  const [index, setIndex] = useState<Index | null>(null);
  const [feed, setFeed] = useState<CityFeed | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => new Date());
  const [lastCity, setLastCity] = usePersistent<string | null>("lastCity", null);
  const [saved, setSaved] = usePersistent<string[]>(`saved:${route.city ?? "_"}`, []);
  const [theme, setTheme] = usePersistent<"auto" | "light" | "dark">("theme", "auto");
  const demo = isDemo();

  useEffect(() => {
    loadIndex().then(setIndex).catch((e: Error) => setError(e.message));
    const t = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!route.city && lastCity && index?.cities.some((c) => c.slug === lastCity) && location.pathname === url() && !location.search) {
      go({ city: lastCity, view: "feed" }, true);
    }
  }, [index]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    if (!route.city) {
      setFeed(null);
      return;
    }
    if (feed?.city === route.city) return;
    setFeed(null);
    loadCity(route.city)
      .then((f) => {
        setFeed(f);
        setLastCity(f.city);
      })
      .catch((e: Error) => setError(`Couldn't load ${route.city}: ${e.message}`));
  }, [route.city]);
  useEffect(() => {
    const city = feed ? `${feed.city_name} · ` : "";
    document.title = `${city}GetOffTheCouch · ur city made easy`;
  }, [feed]);

  const ctx = useMemo<AppCtx | null>(() => {
    if (!index) return null;
    const labels = Object.fromEntries(Object.entries(index.taxonomy).map(([k, v]) => [k, v.label]));
    const neighborhoods: Record<string, [number, number]> = {};
    const sourceNames: Record<string, string> = {};
    for (const s of feed?.sources ?? []) sourceNames[s.source_id] = s.name;
    const byId = new Map((feed?.events ?? []).map((e) => [e.id, e]));
    setTitleLookup((id) => byId.get(id)?.title);
    return {
      index,
      feed,
      route,
      go,
      labels,
      neighborhoods,
      sourceNames,
      byId,
      saved,
      toggleSave: (id: string) => setSaved(saved.includes(id) ? saved.filter((x) => x !== id) : [...saved, id]),
      now,
      demo,
    };
  }, [index, feed, route, saved, now]);

  if (error && !index) {
    return (
      <main class="boot">
        <h1>GetOffTheCouch</h1>
        <p class="notice notice-warn">The data isn't available yet ({error}). Run <code>make pipeline</code>, or open <a href="?demo=1">the demo</a>.</p>
      </main>
    );
  }
  if (!ctx || !index) return <main class="boot" aria-busy="true"><div class="spinner" /></main>;

  for (const n of feed?.neighborhoods ?? []) ctx.neighborhoods[n.name] = [n.lat, n.lon];
  const filtered = feed ? applyFilters(feed.events, route.filters, feed.timezone, ctx.neighborhoods, now) : [];
  const upcomingDeadlines = feed ? deadlines(feed.events, now).filter((d) => d.hours <= 24 * 7 && !d.derived).length : 0;
  const summary = index.cities.find((c) => c.slug === route.city);
  const event = route.eventId ? ctx.byId.get(route.eventId) : undefined;
  const view = route.view;

  return (
    <Ctx.Provider value={ctx}>
      {demo && <div class="demo-banner" role="status">DEMO DATA: made-up examples for trying the interface. <a href={`${url()}?demo=0`} target="_self">Switch to real data</a></div>}
      <header class="top">
        <a class="brand" href={url()} aria-label="GetOffTheCouch home">
          <span class="logo"><Icon name="sofa" size={22} /></span>
          <span class="brand-text">
            <strong>GetOffTheCouch</strong>
            <small>ur city made easy</small>
          </span>
        </a>
        <CityPicker />
        <div class="top-right">
          {summary && (
            <button class={`fresh ${summary.stale_sources ? "warn" : "ok"}`} onClick={() => go({ view: "health", eventId: null })} title="Data health">
              <i /> Updated {age(index.generated_at, now)} · {summary.sources_ok}/{summary.sources_total} sources ok
            </button>
          )}
          <button
            class="icon-btn"
            aria-label={`Theme: ${theme}`}
            title={`Theme: ${theme}`}
            onClick={() => setTheme(theme === "auto" ? "dark" : theme === "dark" ? "light" : "auto")}
          >
            <Icon name={theme === "dark" ? "moon" : "sun"} />
          </button>
        </div>
      </header>
      {route.city && (
        <nav class="tabs" aria-label="Views">
          {TABS.map((t) => (
            <a
              key={t.view}
              href={build({ city: route.city, view: t.view })}
              class={view === t.view && !route.eventId ? "on" : ""}
              aria-current={view === t.view ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                go({ view: t.view, eventId: null });
              }}
            >
              <Icon name={t.icon} size={16} />
              <span>{t.label}</span>
              {t.view === "deadlines" && upcomingDeadlines > 0 && <b class="count">{upcomingDeadlines}</b>}
              {t.view === "saved" && saved.length > 0 && <b class="count muted">{saved.length}</b>}
            </a>
          ))}
        </nav>
      )}
      <main class="main" id="main">
        {!route.city && (view === "about" ? <About /> : <Home />)}
        {route.city && !feed && !error && <div class="spinner" aria-busy="true" />}
        {route.city && error && !feed && <p class="notice notice-warn">{error}</p>}
        {feed && (
          <>
            {FILTERED_VIEWS.includes(view) && <FilterBar resultCount={filtered.length} />}
            {view === "feed" && <Feed events={filtered} />}
            {view === "calendar" && <Calendar events={filtered} />}
            {view === "map" && <MapView events={filtered} />}
            {view === "deadlines" && <Deadlines events={feed.events} />}
            {view === "plan" && <Plan events={feed.events} />}
            {view === "saved" && <Saved />}
            {view === "health" && <Health />}
            {view === "about" && <About />}
          </>
        )}
      </main>
      {event && <EventDrawer e={event} />}
      <footer class="foot">
        <p>
          <strong>GetOffTheCouch</strong> · no made-up data: every card names its source and when we last checked.{" "}
          <a href={url("about/")}>How it works</a> ·{" "}
          <a href={route.city ? build({ city: route.city, view: "health" }) : url("health/")}>Data health</a>
        </p>
        <p class="muted small">Map data © OpenStreetMap contributors. Event data © the original publishers, linked on every card.</p>
      </footer>
    </Ctx.Provider>
  );
}
