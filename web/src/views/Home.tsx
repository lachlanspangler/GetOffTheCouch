import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";

export function Home() {
  const { index, go } = useApp();
  const cities = [...index.cities].sort((a, b) => b.events - a.events || a.name.localeCompare(b.name));
  return (
    <div class="home">
      <section class="hero">
        <h1>
          New in town?<br />
          <span class="accent">Get off the couch.</span>
        </h1>
        <p class="lead">
          Everything worth leaving the house for in your new city: beer leagues, block parties, concerts with live prices, volunteering,
          cons and faires, trivia and run clubs. Plus every deadline you'd otherwise miss.
        </p>
      </section>
      <section>
        <h2 class="section-title">Pick your city</h2>
        <div class="city-grid">
          {cities.map((c) => (
            <button key={c.slug} class="city-card" onClick={() => go({ city: c.slug, view: "feed", eventId: null })}>
              <span class="city-name">{c.name}<span class="muted">, {c.state}</span></span>
              <span class="city-stats">
                {c.events > 0 ? (
                  <>
                    <span><strong>{c.upcoming_7d}</strong> this week</span>
                    <span><strong>{c.deadlines}</strong> deadlines</span>
                  </>
                ) : (
                  <span class="muted">Sources coming soon</span>
                )}
              </span>
              <span class="city-health">
                <i class={c.sources_ok === c.sources_total ? "ok" : c.sources_ok ? "warn" : "off"} />
                {c.sources_ok}/{c.sources_total} sources healthy{c.sources_disabled ? ` · ${c.sources_disabled} awaiting API keys` : ""}
              </span>
              <Icon name="right" size={18} class="city-go" />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
