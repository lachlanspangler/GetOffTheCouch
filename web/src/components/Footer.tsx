// Site footer (DESIGN.md §4.14): cities, popular pages for the current city, company links, data status.
import { useApp } from "../lib/ctx";
import { build } from "../lib/router";
import { HUBS, url } from "../lib/site";
import { fmtDay, fmtTime, tzAbbr } from "../lib/time";

export const REPO = "https://github.com/lachlanspangler/GetOffTheCouch";
export const reportGeneral = `${REPO}/issues/new?labels=data-report&title=${encodeURIComponent("Report a problem")}`;
export const suggestSource = `${REPO}/issues/new?labels=source-suggestion&title=${encodeURIComponent("Source suggestion: ")}&body=${encodeURIComponent("City:\nSource name and URL:\nWhat it lists:\n")}`;

export type Theme = "auto" | "light" | "dark";

export function Footer({ theme, setTheme }: { theme: Theme; setTheme: (t: Theme) => void }) {
  const { index, route, feed } = useApp();
  const city = route.city;
  const summary = index.cities.find((c) => c.slug === city);
  const stale = summary ? summary.stale_sources > 0 : index.cities.some((c) => c.stale_sources > 0);
  const tz = feed?.timezone ?? "America/New_York";
  const popular = ["this-weekend", "free", "concerts", "trivia", "beer-leagues", "volunteering"];
  return (
    <footer class="footer">
      <div class="container">
        <div class="footer-grid">
          <div>
            <a class="wordmark" href={url()}>Get Off the Couch</a>
            <p class="desc">Everything worth leaving the house for in your city, and every deadline you'd otherwise miss. From official sources, checked every few hours.</p>
          </div>
          <div>
            <h2>Cities</h2>
            <ul>
              {[...index.cities].sort((a, b) => b.events - a.events).slice(0, 12).sort((a, b) => a.name.localeCompare(b.name)).map((c) => (
                <li key={c.slug}><a href={build({ city: c.slug, view: "feed" })}>{c.name}</a></li>
              ))}
              <li><a href={url("cities/")}>All {index.cities.length} cities and coverage</a></li>
            </ul>
          </div>
          <div>
            {feed && city ? (
              <>
                <h2>Popular in {feed.city_name}</h2>
                <ul>
                  {popular.map((slug) => {
                    const h = HUBS.find((x) => x.slug === slug)!;
                    return <li key={slug}><a href={url(`${city}/${slug}/`)}>{h.label}</a></li>;
                  })}
                  <li><a href={build({ city, view: "deadlines" })}>Sign-up deadlines</a></li>
                  <li><a href={url(`${city}/new.xml`)}>New listings (RSS/Atom)</a></li>
                </ul>
              </>
            ) : (
              <>
                <h2>About</h2>
                <ul>
                  <li><a href={url("about/")}>About us</a></li>
                  <li><a href={url("methodology/")}>How we get the data</a></li>
                  <li><a href={url("privacy/")}>Privacy</a></li>
                </ul>
              </>
            )}
          </div>
          <div>
            <h2>{feed ? "About" : "Help"}</h2>
            <ul>
              {feed && <li><a href={url("about/")}>About us</a></li>}
              {feed && <li><a href={url("methodology/")}>How we get the data</a></li>}
              <li>
                <a href={city ? build({ city, view: "health" }) : url("health/")}>
                  <span class={`status-dot ${stale ? "warn" : ""}`} aria-hidden="true" />
                  Data status
                </a>
              </li>
              {feed && <li><a href={url("privacy/")}>Privacy</a></li>}
              <li><a href={reportGeneral} target="_blank" rel="noopener noreferrer">Report a problem</a></li>
              <li><a href={suggestSource} target="_blank" rel="noopener noreferrer">Suggest a source</a></li>
            </ul>
          </div>
        </div>
        <div class="fine">
          <span>
            Event details belong to their organizers; every listing links to the original. Map data and some locations © OpenStreetMap contributors.
            {" "}Updated {fmtDay(index.generated_at, tz)}, {fmtTime(index.generated_at, tz)} {tzAbbr(index.generated_at, tz)}.
          </span>
          <span class="theme-pick" role="group" aria-label="Appearance">
            Appearance
            {(["auto", "light", "dark"] as Theme[]).map((t) => (
              <button key={t} aria-pressed={theme === t} onClick={() => setTheme(t)}>
                {t === "auto" ? "Auto" : t === "light" ? "Light" : "Dark"}
              </button>
            ))}
          </span>
        </div>
      </div>
    </footer>
  );
}
