import { hydrate, render } from "preact";
import { App, type Initial } from "./app";
import { loadCity, loadIndex } from "./lib/data";
import { parsePath } from "./lib/router";
import { canHydrate, hydration } from "./lib/store";
import { preloadView } from "./lib/views";
import "./styles/app.css";

const el = document.getElementById("app")!;

// Pre-rendered pages (scripts/prerender.mjs) already show real content. Load the same data the server used and
// hydrate in place with the server's clock and no stored state, so the first client render matches the HTML exactly
// (same DOM nodes: no flash, no layout shift, no second LCP). Effects then apply the viewer's clock and saved items.
async function boot(): Promise<void> {
  // Only hydrate when the URL is exactly the pre-rendered page: Pages serves /chicago/index.html for
  // /chicago/?when=weekend too, and hydration never patches attributes (links would point at the wrong events).
  if (el.dataset.ssr && canHydrate(location, sessionStorageDemo())) {
    try {
      const route = parsePath(location.pathname, location.search);
      await preloadView(route.view); // a lazily loaded page must be ready before hydrating its server HTML
      const index = await loadIndex();
      const feed = route.city ? await loadCity(route.city) : null;
      const initial: Initial = { index, feed, route, now: new Date(el.dataset.now ?? index.generated_at) };
      hydration.active = true;
      hydrate(<App initial={initial} />, el);
      hydration.active = false;
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
