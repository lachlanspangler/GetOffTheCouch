import { CityArt } from "../components/Art";
import { CitySearch } from "../components/CityPicker";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { count } from "../lib/format";
import { build } from "../lib/router";
import type { CitySummary } from "../lib/types";

function citySub(c: CitySummary): string {
  if (!c.events) return "Coming soon";
  return `${count(c.upcoming_7d)} this week${c.deadlines ? ` · ${count(c.deadlines)} deadline${c.deadlines === 1 ? "" : "s"}` : ""}`;
}

export function Home() {
  const { index } = useApp();
  const cities = [...index.cities].sort((a, b) => b.events - a.events || a.name.localeCompare(b.name));
  const total = index.cities.reduce((n, c) => n + c.events, 0);
  return (
    <div class="container">
      <section class="hero">
        <p class="kicker">Your city, made easy.</p>
        <h1>Everything worth leaving the house for, and every deadline you'd otherwise miss.</h1>
        <p class="lede">
          Rec leagues, block parties, concerts (with prices wherever venues publish them), volunteering, trivia, cons and faires, in one place for each city. We pull it
          from official calendars and venues, check it every few hours, and tell you where every listing came from.
        </p>
        <CitySearch />
      </section>
      <section class="section" aria-labelledby="cities" style={{ marginTop: "0" }}>
        <div class="section-head">
          <div>
            <h2 id="cities">Cities</h2>
            <p class="small">{count(total)} upcoming events across {index.cities.length} cities.</p>
          </div>
        </div>
        {cities.length <= 12 ? (
          <div class="tiles cities">
            {cities.map((c) => (
              <div class="tile" key={c.slug}>
                <CityArt slug={c.slug} ratio="3/1" />
                <h3><a href={build({ city: c.slug, view: "feed" })}>{c.name}</a></h3>
                <p class="sub">{citySub(c)}</p>
                <Icon name="right" size={18} class="chev" />
              </div>
            ))}
          </div>
        ) : (
          <ul class="city-index">
            {[...cities].sort((a, b) => a.name.localeCompare(b.name)).map((c) => (
              <li key={c.slug}>
                <a href={build({ city: c.slug, view: "feed" })}>{c.name}</a>
                <span class="sub">{citySub(c)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section class="section" aria-labelledby="how">
        <h2 id="how" class="sr-only">How it works</h2>
        <div class="how">
          <div>
            <h3>From official sources</h3>
            <p>Park districts, libraries, universities, venues and open-data portals. We use their published feeds and follow their rules.</p>
          </div>
          <div>
            <h3>Checked every few hours</h3>
            <p>Every listing says when we last checked it. If a source goes quiet, we say so instead of showing old events as new.</p>
          </div>
          <div>
            <h3>Deadlines, not just dates</h3>
            <p>League sign-ups, registration cutoffs, early-bird prices and the state paperwork for new residents, soonest first.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
