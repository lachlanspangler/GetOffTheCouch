import { hydrate, render } from "preact";
import { App, type Initial } from "./app";
import { loadCity, loadIndex } from "./lib/data";
import { parsePath } from "./lib/router";
import { hydration } from "./lib/store";
import "./styles/app.css";

const el = document.getElementById("app")!;

// Pre-rendered pages (scripts/prerender.mjs) already show real content. Load the same data the server used and
// hydrate in place with the server's clock and no stored state, so the first client render matches the HTML exactly
// (same DOM nodes: no flash, no layout shift, no second LCP). Effects then apply the viewer's clock and saved items.
async function boot(): Promise<void> {
  if (el.dataset.ssr && !location.hash.startsWith("#/")) {
    try {
      const route = parsePath(location.pathname, location.search);
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
  render(<App />, el);
}

void boot();
