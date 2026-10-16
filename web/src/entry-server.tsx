// SSR entry for scripts/prerender.mjs: render one route to HTML plus its <head> tags, from the same data files
// the browser reads. Effects don't run on the server, so pages show their finished, data-driven state.
import renderToString from "preact-render-to-string";
import { App } from "./app";
import { parsePath } from "./lib/router";
import { headFor, headHtml } from "./lib/seo";
import type { CityFeed, Index } from "./lib/types";

export function render(path: string, index: Index, feed: CityFeed | null, now: Date): { html: string; head: string; status: number } {
  const [p, q = ""] = path.split("?");
  const route = parsePath(p, q);
  const event = route.eventId && feed ? feed.events.find((e) => e.id === route.eventId) : undefined;
  const html = renderToString(<App initial={{ index, feed, route, now }} />);
  const head = headFor(route, index, feed, event, now);
  return { html, head: headHtml(head), status: route.unknown || (route.eventId && !event) ? 404 : 200 };
}

export { headFor } from "./lib/seo";
export { eventPath } from "./lib/site";
