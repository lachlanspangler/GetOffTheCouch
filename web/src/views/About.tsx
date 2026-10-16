import { useApp } from "../lib/ctx";

export function About() {
  const { index } = useApp();
  return (
    <article class="about prose">
      <h2>How GetOffTheCouch works</h2>
      <p>
        Moving to a new city is lonely, and the good stuff is scattered across 40 websites. We pull it into one place for each city and
        refresh it all day: rec leagues, block parties, concerts, volunteering, cons and faires, trivia and run clubs. We also put every
        deadline you'd otherwise miss in the same place.
      </p>
      <h3>Our data rules</h3>
      <ul>
        <li><strong>No made-up data, ever.</strong> Every field is reported by a source, derived from one, read from listing text, or estimated. Estimates always say so.</li>
        <li><strong>Estimates come with ranges.</strong> "~1,200 people (900–1,500)" shows how we got the number and how sure we are. We never show false precision.</li>
        <li><strong>Every card says where it came from</strong> and when we last checked.</li>
        <li><strong>Broken sources are announced, not hidden.</strong> See the Health page. Old data is marked stale.</li>
        <li><strong>We play nice with sources.</strong> We prefer official APIs and open data, follow robots.txt and terms of service, and keep our request rates low.</li>
        <li><strong>Your preferences stay on your device.</strong> We have no accounts and no tracking.</li>
      </ul>
      <h3>How we estimate</h3>
      <ul>
        <li><strong>Crowd size</strong> comes from venue capacity × typical fill for the ticket status (sold out, on sale…). Without a capacity, we use a typical range for the category, at low confidence.</li>
        <li><strong>"Tickets left"</strong> appears only when a seller signal backs it, such as resale listings compared with the most we've seen. We label it, because listings aren't seats.</li>
        <li><strong>Deadlines</strong> come from structured registration fields, or from phrases like "register by Nov 3" with the original sentence shown.</li>
        <li><strong>"Good for meeting people"</strong> combines the category (leagues and volunteering score high), whether it repeats, solo-friendliness and crowd size.</li>
      </ul>
      <p class="muted small">Data schema v{index.schema_version} · generated {index.generated_at}</p>
    </article>
  );
}
