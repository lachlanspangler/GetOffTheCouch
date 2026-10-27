import { hydrate, render } from "preact";
import { App, type Initial } from "./app";
import { city, loadCity, loadIndex } from "./lib/data";
import { replay, routeSig, type InitialData } from "./lib/partial";
import { parsePath } from "./lib/router";
import { canHydrate, hydration } from "./lib/store";
import { preloadView } from "./lib/views";
import "./styles/app.css";

const el = document.getElementById("app")!;

/** The page's inline first-render data (I-117), if the pre-renderer could make an exact one for it. */
function inline(): InitialData | null {
  const s = document.getElementById("gotc-initial");
  if (!s?.textContent) return null;
  try {
    const d = JSON.parse(s.textContent) as InitialData;
    return d.v === 1 ? d : null;
  } catch {
    return null;
  }
}

// Pre-rendered pages (scripts/prerender.mjs) already show real content. Hydrate in place with the server's clock and
// no stored state, so the first client render matches the HTML exactly (same DOM nodes: no flash, no layout shift,
// no second LCP). The page inlines exactly the events it shows plus the whole-feed numbers it computed, so hydration
// only waits for index.json; the city's shards then load in the background. Effects apply the viewer's clock and
// saved items afterwards.
async function boot(): Promise<void> {
  // Only hydrate when the URL is exactly the pre-rendered page: Pages serves /chicago/index.html for
  // /chicago/?when=weekend too, and hydration never patches attributes (links would point at the wrong events).
  if (el.dataset.ssr && canHydrate(location, sessionStorageDemo())) {
    try {
      const route = parsePath(location.pathname, location.search);
      const data = inline();
      const fromPage = !!(data && route.city && data.feed.city === route.city && data.sig === routeSig(route));
      const [index, feed] = await Promise.all([
        loadIndex(),
        route.city ? (fromPage ? Promise.resolve(data!.feed) : loadCity(route.city)) : Promise.resolve(null),
        preloadView(route.view), // a lazily loaded page must be ready before hydrating its server HTML
      ]);
      if (fromPage && feed) {
        replay(feed, data!.sig, data!.memo);
        city(feed.city).hint(data!.where ?? {});
      }
      const initial: Initial = { index, feed, route, now: new Date(el.dataset.now ?? index.generated_at) };
      hydration.active = true;
      hydrate(<App initial={initial} />, el);
      hydration.active = false;
      performance.mark?.("gotc:hydrated");
      return;
    } catch {
      el.textContent = "";
    }
  }
  if (el.dataset.ssr) el.textContent = ""; // e.g. an old #/ link landed on the pre-rendered home page
  render(<App />, el);
}

function sessionStorageDemo(): boolean {
  try {
    return sessionStorage.getItem("gotc:demo") === "1";
  } catch {
    return false;
  }
}

void boot();
