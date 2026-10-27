import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { Footer, type Theme } from "./components/Footer";
import { Header } from "./components/Header";
import { Icon } from "./components/Icon";
import { SkeletonRows } from "./components/EventRow";
import { Ctx, type AppCtx } from "./lib/ctx";
import { city, isDemo, loadIndex, needFor, priority } from "./lib/data";
import { isInline, memo, routeSig, setRenderSig } from "./lib/partial";
import { applyFilters, deadlines } from "./lib/filters";
import { recordSignal } from "./lib/recommend";
import { build, setTitleLookup, useRoute, type Route } from "./lib/router";
import { url } from "./lib/site";
import { usePersistent } from "./lib/store";
import { pageTitle } from "./lib/title";
import { useView, type LazyName } from "./lib/views";
import type { CityFeed, Index } from "./lib/types";
import { EventPage } from "./views/EventPage";
import { Feed } from "./views/Feed";
import { Home } from "./views/Home";

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
  const [loaded, setFeed] = useState<CityFeed | null>(initial?.feed ?? null);
  // true once every shard of the city is in (an inline pre-rendered feed or the first shards are not)
  const [complete, setComplete] = useState(() => !!initial?.feed && !isInline(initial.feed));
  // ...including the past weeks' shards, which only saved items and ended events' pages need
  const [everything, setEverything] = useState(complete);
  const firstSig = useRef(initial?.route ? routeSig(initial.route) : "");
  const [error, setError] = useState<string | null>(null);
  const [clock, setNow] = useState(() => initial?.now ?? new Date());
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
    // the shards this view needs first (current + next week for the default feed), the rest of the city in idle time
    if (!route.city) {
      setFeed(null);
      return;
    }
    const c = city(route.city);
    let live = true;
    const done = (f: CityFeed, all: boolean) => {
      if (live && all) {
        setFeed(f);
        setComplete(true);
      }
    };
    const have = loaded?.city === route.city;
    if (have && complete) return;
    setError(null);
    if (!have) {
      setFeed(null);
      setComplete(false);
      setEverything(false);
      const need = needFor(route.view, route.filters.when, route.eventId, now);
      c.ensure(need)
        .then((f) => {
          if (!live) return;
          setFeed((cur) => (cur && cur.city === f.city && cur.events.length >= f.events.length ? cur : f));
          if (need.all) setComplete(true);
          if (need.past) setEverything(true);
        })
        .catch((e: Error) => live && setError(e.message));
    }
    c.prefetch(done, priority(now));
    return () => {
      live = false;
      c.off(done);
    };
  }, [route.city, retry]);
  useEffect(() => {
    // a filter, view or event that needs shards we haven't loaded yet (e.g. "Next 30 days", the calendar)
    if (!route.city || !loaded || loaded.city !== route.city) return;
    const need = needFor(route.view, route.filters.when, route.eventId, now);
    if (complete && (everything || !need.past)) return;
    if (isInline(loaded) && routeSig(route) === firstSig.current) return; // still the pre-rendered page
    let live = true;
    city(route.city)
      .ensure(need)
      .then((f) => {
        if (!live) return;
        setFeed((cur) => (cur && !isInline(cur) && cur.events.length >= f.events.length ? cur : f));
        if (need.all) setComplete(true);
        if (need.past) setEverything(true);
      })
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [route, complete]);

  setRenderSig(routeSig(route));
  // an inline feed holds only what the pre-rendered page showed: on any other page, wait for the real data
  const feed = isInline(loaded) && routeSig(route) !== firstSig.current ? null : loaded;
  // ...and keep the server's clock until it has: the inline data was checked against the page at that time only
  const now = isInline(feed) && initial?.now ? initial.now : clock;
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
    document.title = pageTitle(route, feed, event, now);
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
  const soon = feed ? memo(feed, "hdr:deadlines", () => new Set(deadlines(feed.events, now).filter((d) => d.hours <= 24 * 7 && !d.derived && d.kind === "closes").map((d) => d.event.series_id ?? d.event.id)).size) : 0;
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
        {!route.city && view === "about" && <Lazy name="about" />}
        {!route.city && view === "methodology" && <Lazy name="methodology" />}
        {!route.city && view === "privacy" && <Lazy name="privacy" />}
        {!route.city && view === "health" && <Lazy name="health" />}
        {!route.city && view === "cities" && <Lazy name="cities" />}
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
        {feed && route.eventId && !event && !(complete && everything) && <div class="container" style={{ paddingTop: "32px" }}><SkeletonRows /></div>}
        {feed && route.eventId && !event && complete && everything && (
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
                {view === "calendar" && <Lazy name="calendar" props={{ events: applyFilters(feed.events, { ...route.filters, when: "all" }, feed.timezone, ctx.neighborhoods, now) }} />}
                {view === "map" && <Lazy name="map" props={{ events: filtered }} />}
                {view === "deadlines" && <Lazy name="deadlines" props={{ events: feed.events }} />}
                {view === "plan" && <Lazy name="plan" props={{ events: feed.events }} />}
                {view === "saved" && <Lazy name="saved" />}
                {view === "health" && <Lazy name="health" />}
                {view === "about" && <Lazy name="about" />}
                {view === "methodology" && <Lazy name="methodology" />}
                {view === "privacy" && <Lazy name="privacy" />}
              </>
            )}
          </>
        )}
      </main>
      <Footer theme={theme} setTheme={setTheme} />
    </Ctx.Provider>
  );
}


function Lazy({ name, props }: { name: LazyName; props?: Record<string, unknown> }) {
  const C = useView(name);
  return C ? <C {...(props ?? {})} /> : <div class="container" style={{ paddingTop: "32px" }}><SkeletonRows n={3} /></div>;
}
