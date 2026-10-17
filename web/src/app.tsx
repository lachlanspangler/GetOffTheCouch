import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { Footer, type Theme } from "./components/Footer";
import { Header } from "./components/Header";
import { Icon } from "./components/Icon";
import { SkeletonRows } from "./components/EventRow";
import { Ctx, type AppCtx } from "./lib/ctx";
import { isDemo, loadCity, loadIndex } from "./lib/data";
import { applyFilters, deadlines } from "./lib/filters";
import { recordSignal } from "./lib/recommend";
import { build, setTitleLookup, useRoute, type Route } from "./lib/router";
import { url } from "./lib/site";
import { usePersistent } from "./lib/store";
import { pageTitle } from "./lib/seo";
import type { CityFeed, Index } from "./lib/types";
import { About, Methodology, Privacy } from "./views/About";
import { Calendar } from "./views/Calendar";
import { Deadlines } from "./views/Deadlines";
import { EventPage } from "./views/EventPage";
import { Feed } from "./views/Feed";
import { Health } from "./views/Health";
import { Home } from "./views/Home";
import { MapView } from "./views/MapView";
import { Plan } from "./views/Plan";
import { Saved } from "./views/Saved";

function applyTheme(t: Theme): void {
  const dark = t === "dark" || (t === "auto" && typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

export interface Initial {
  index: Index;
  feed: CityFeed | null;
  route?: Route;
  now?: Date;
}

export function App({ initial }: { initial?: Initial } = {}) {
  const [route, go] = useRoute(initial?.route);
  const [index, setIndex] = useState<Index | null>(initial?.index ?? null);
  const [feed, setFeed] = useState<CityFeed | null>(initial?.feed ?? null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => initial?.now ?? new Date());
  const [lastCity, setLastCity] = usePersistent<string | null>("lastCity", null);
  const [saved, setSaved] = usePersistent<string[]>(`saved:${route.city ?? "_"}`, []);
  const [theme, setTheme] = usePersistent<Theme>("theme", "auto");
  const [retry, setRetry] = useState(0);
  const demo = isDemo();

  useEffect(() => {
    if (!index) loadIndex().then(setIndex).catch((e: Error) => setError(e.message));
    setNow(new Date());
    const t = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!route.city && route.view === "feed" && lastCity && index?.cities.some((c) => c.slug === lastCity) && location.pathname === url() && !location.search) {
      go({ city: lastCity, view: "feed" }, true);
    }
  }, [index]);
  useEffect(() => {
    applyTheme(theme);
    if (theme !== "auto" || typeof matchMedia !== "function") return;
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const on = () => applyTheme("auto");
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [theme]);
  useEffect(() => {
    if (!route.city) {
      setFeed(null);
      return;
    }
    if (feed?.city === route.city) return;
    setFeed(null);
    setError(null);
    loadCity(route.city)
      .then((f) => {
        setFeed(f);
        setLastCity(f.city);
      })
      .catch((e: Error) => setError(e.message));
  }, [route.city, retry]);

  const ctx = useMemo<AppCtx | null>(() => {
    if (!index) return null;
    const labels = Object.fromEntries(Object.entries(index.taxonomy).map(([k, v]) => [k, v.label]));
    const neighborhoods: Record<string, [number, number]> = {};
    for (const n of feed?.neighborhoods ?? []) neighborhoods[n.name] = [n.lat, n.lon];
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
      toggleSave: (id: string) => {
        const ev = byId.get(id);
        if (ev) recordSignal(ev, saved.includes(id) ? "unsave" : "save"); // on-device ranking signal (rank v2)
        setSaved(saved.includes(id) ? saved.filter((x) => x !== id) : [...saved, id]);
      },
      now,
      demo,
    };
  }, [index, feed, route, saved, now]);

  const event = route.eventId && ctx ? ctx.byId.get(route.eventId) : undefined;
  useEffect(() => {
    if (feed) setLastCity(feed.city); // also for visitors who landed on a pre-rendered city page
  }, [feed?.city]);
  useEffect(() => {
    // old #/city/event/evt_x links become /city/events/<hex>/ before titles are known: swap in the canonical
    // (pre-rendered) URL once they are, so reloads and shares don't hit a 404
    if (event && route.eventId) {
      const want = build({ city: route.city, eventId: route.eventId });
      if (location.pathname !== want.split("?")[0]) history.replaceState(history.state, "", want);
    }
  }, [event?.id]);
  const first = useRef(true);
  useEffect(() => {
    // client-side navigation: move focus to the new page so screen readers don't lose their place
    if (first.current) {
      first.current = false;
      return;
    }
    if (!route.eventId) document.getElementById("main")?.focus({ preventScroll: true });
  }, [route.city, route.view, route.hub, route.eventId]);
  useEffect(() => {
    document.title = pageTitle(route, feed, event);
  }, [feed, route, event]);

  if (error && !index) {
    return (
      <main class="boot">
        <h1>Get Off the Couch</h1>
        <p class="notice notice-critical"><Icon name="alert" size={16} /> We couldn't load the listings. Your connection may have dropped ({error}).</p>
        <p style={{ marginTop: "16px" }}><button class="btn" onClick={() => location.reload()}>Try again</button></p>
      </main>
    );
  }
  if (!ctx || !index) {
    return (
      <main class="boot container" aria-busy="true">
        <SkeletonRows n={4} />
      </main>
    );
  }

  const filtered = feed ? applyFilters(feed.events, route.filters, feed.timezone, ctx.neighborhoods, now) : [];
  const soon = feed ? new Set(deadlines(feed.events, now).filter((d) => d.hours <= 24 * 7 && !d.derived && d.kind === "closes").map((d) => d.event.series_id ?? d.event.id)).size : 0;
  const view = route.view;
  const unknownCity = route.city && !index.cities.some((c) => c.slug === route.city);
  const unknownHub = !!route.unknown;

  return (
    <Ctx.Provider value={ctx}>
      {demo && (
        <div class="demo-bar" role="status">
          Sample data. These events aren't real. <a href={`${url()}?demo=0`} target="_self">See live cities</a>
        </div>
      )}
      <a class="skip" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <Header deadlineCount={soon} />
      <main class="main" id="main" tabIndex={-1}>
        {!route.city && view === "about" && <About />}
        {!route.city && view === "methodology" && <Methodology />}
        {!route.city && view === "privacy" && <Privacy />}
        {!route.city && view === "health" && <Health />}
        {!route.city && view === "feed" && <Home />}
        {unknownCity && (
          <div class="container empty">
            <h1>We don't cover that city yet.</h1>
            <p>Pick one of the cities we cover, or suggest yours from the link at the bottom of the page.</p>
            <a class="btn btn-secondary" href={url()}>See all cities</a>
          </div>
        )}
        {route.city && !unknownCity && !feed && !error && <div class="container" style={{ paddingTop: "32px" }}><SkeletonRows /></div>}
        {route.city && !unknownCity && error && !feed && (
          <div class="container empty">
            <h1>We couldn't load {index.cities.find((c) => c.slug === route.city)?.name ?? route.city}'s events.</h1>
            <p>Your connection may have dropped.</p>
            <button class="btn btn-secondary" onClick={() => setRetry(retry + 1)}>Try again</button>
          </div>
        )}
        {feed && route.eventId && !event && (
          <div class="container empty">
            <h1>This event has ended or moved.</h1>
            <p>It's no longer listed by its source. Here's what's on in {feed.city_name} instead.</p>
            <a class="btn btn-secondary" href={url(`${feed.city}/`)}>What's on in {feed.city_name}</a>
          </div>
        )}
        {feed && event && <EventPage e={event} />}
        {feed && !route.eventId && (
          <>
            {unknownHub ? (
              <div class="container empty">
                <h1>We couldn't find that page.</h1>
                <p>It may have moved. Here's everything on in {feed.city_name}.</p>
                <a class="btn btn-secondary" href={url(`${feed.city}/`)}>What's on in {feed.city_name}</a>
              </div>
            ) : (
              <>
                {view === "feed" && <Feed events={filtered} />}
                {view === "calendar" && <Calendar events={filtered} />}
                {view === "map" && <MapView events={filtered} />}
                {view === "deadlines" && <Deadlines events={feed.events} />}
                {view === "plan" && <Plan events={feed.events} />}
                {view === "saved" && <Saved />}
                {view === "health" && <Health />}
                {view === "about" && <About />}
                {view === "methodology" && <Methodology />}
                {view === "privacy" && <Privacy />}
              </>
            )}
          </>
        )}
      </main>
      <Footer theme={theme} setTheme={setTheme} />
    </Ctx.Provider>
  );
}

