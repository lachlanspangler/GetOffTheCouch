import { render } from "preact";
import { App, type Initial } from "./app";
import { loadCity, loadIndex } from "./lib/data";
import { parsePath } from "./lib/router";
import "./styles/app.css";

const el = document.getElementById("app")!;

// Pre-rendered pages (scripts/prerender.mjs) already show real content. Keep it on screen while the data loads,
// then swap in the live app in a single task (no paint in between), so there's never a loading state on top of a
// finished page. A fresh render (not hydrate) means times like "today" are always computed with the viewer's clock.
async function boot(): Promise<void> {
  if (el.dataset.ssr && !location.hash.startsWith("#/")) {
    try {
      const route = parsePath(location.pathname, location.search);
      const index = await loadIndex();
      const feed = route.city ? await loadCity(route.city) : null;
      const initial: Initial = { index, feed, route };
      el.textContent = "";
      render(<App initial={initial} />, el);
      return;
    } catch {
      el.textContent = "";
    }
  }
  render(<App />, el);
}

void boot();
