// About, methodology and privacy: plain prose pages with a table of contents (DESIGN.md §5).
import type { ComponentChildren } from "preact";
import { useApp } from "../lib/ctx";
import { count } from "../lib/format";
import { build } from "../lib/router";
import { url } from "../lib/site";
import { reportGeneral, suggestSource, REPO } from "../components/Footer";

function Page({ title, lede, toc, children }: { title: string; lede: string; toc: [string, string][]; children: ComponentChildren }) {
  return (
    <div class="container">
      <div class="prose-layout">
        <nav class="toc" aria-label="On this page">
          <h2>On this page</h2>
          <ul>{toc.map(([id, label]) => <li key={id}><a href={`#${id}`}>{label}</a></li>)}</ul>
        </nav>
        <article class="prose">
          <h1>{title}</h1>
          <p class="lede">{lede}</p>
          {children}
        </article>
      </div>
    </div>
  );
}

export function About() {
  const { index } = useApp();
  const events = index.cities.reduce((n, c) => n + c.events, 0);
  const sources = index.cities.reduce((n, c) => n + c.sources_ok, 0);
  return (
    <Page
      title="About Get Off the Couch"
      lede="A guide to what's on in your city, built for people who just moved there."
      toc={[["what", "What this is"], ["how", "How it works"], ["dont", "What we don't do"], ["who", "Who's behind it"], ["contact", "Contact"]]}
    >
      <h2 id="what">What this is</h2>
      <p>
        Moving to a new city is lonely, and the good stuff is spread across dozens of websites: the park district's program guide, the
        library calendar, the rec league's sign-up page, the venue's own listings. Get Off the Couch puts it in one place for each city
        and keeps it current: rec and beer leagues, block parties and new openings, concerts with prices, volunteering, trivia, cons and
        faires, and the deadlines that come with them.
      </p>
      <p>
        Right now that's {count(events)} upcoming events in {index.cities.length} cities, from {count(sources)} sources that are up to date.
      </p>
      <h2 id="how">How it works</h2>
      <p>
        Every few hours, our pipeline reads each source's published feed or open-data API, checks each record against a strict schema,
        merges duplicates (the same concert on a venue's site and a ticket site becomes one listing with both prices), and publishes
        this site. Every listing shows where it came from and when we last checked it. The full details are on the{" "}
        <a href={url("methodology/")}>methodology page</a>, and the live state of every source is on the{" "}
        <a href={url("health/")}>data status page</a>.
      </p>
      <h2 id="dont">What we don't do</h2>
      <ul>
        <li><strong>We don't make things up.</strong> If a source doesn't give a price or a deadline, we don't guess one. Estimates, like crowd size, are labeled as estimates and always come with a range.</li>
        <li><strong>We don't sell tickets or take sign-ups.</strong> Every button takes you to the organizer or the seller.</li>
        <li><strong>We don't sell placement.</strong> Nothing on this site is sponsored or promoted. Picks are chosen by a ranking you can read about, and each one says why it's there.</li>
        <li><strong>We don't track you.</strong> No accounts, no ad trackers, no analytics cookies. See the <a href={url("privacy/")}>privacy page</a>.</li>
        <li><strong>We don't scrape where we're not welcome.</strong> We use official APIs and feeds first, follow each site's robots.txt and terms, and keep our request rates low.</li>
      </ul>
      <h2 id="who">Who's behind it</h2>
      <p>
        Get Off the Couch is an independent project. The code and the data pipeline are open on <a href={REPO}>GitHub</a>, including the list of
        every source we use and why we trust it.
      </p>
      <h2 id="contact">Contact</h2>
      <p>
        Spotted something wrong? Every event page has a "Report a problem" link, or you can <a href={reportGeneral} target="_blank" rel="noopener noreferrer">report a problem here</a>.
        Know a calendar we should include? <a href={suggestSource} target="_blank" rel="noopener noreferrer">Suggest a source</a>. If you run an event
        and want your listing changed or removed, open an issue and we'll handle it within a few days.
      </p>
    </Page>
  );
}

export function Methodology() {
  const { index, route } = useApp();
  const status = route.city ? build({ city: route.city, view: "health" }) : url("health/");
  return (
    <Page
      title="How we get the data"
      lede="Where listings come from, how we keep them fresh, and exactly what we estimate."
      toc={[["sources", "Sources"], ["fresh", "Freshness"], ["dedupe", "Duplicates"], ["deadlines", "Deadlines"], ["estimates", "Estimates"], ["ranking", "How picks are chosen"], ["limits", "Known limits"]]}
    >
      <h2 id="sources">Sources</h2>
      <p>
        We read from four kinds of places: city and state open-data portals (park events, street permits, new liquor licenses), library and
        university calendars, venues' own listings (where they publish structured data), and organizations that run leagues, volunteering
        and trivia. We prefer an official API or feed over a web page, follow each site's robots.txt and terms of service, and identify
        ourselves in every request. When a site asks bots not to visit, we don't.
      </p>
      <p>
        Some sources, like Ticketmaster and SeatGeek, need an API key we don't have yet. They're built and tested but switched off, and they
        show as "Not connected" on the <a href={status}>data status page</a>.
      </p>
      <h2 id="fresh">Freshness</h2>
      <p>
        Each source has a schedule and a freshness target. If a fetch fails, we retry with increasing waits. If a source keeps failing, we
        stop asking so often, keep showing its last good listings and label them "may be out of date". A source that suddenly returns far
        fewer events than usual is treated as a problem, not as news.
      </p>
      <h2 id="dedupe">Duplicates</h2>
      <p>
        The same event often appears in several places. We merge listings that happen at the same place within a few hours and have
        nearly the same title. Two records from the same source are never merged. When listings merge, every seller's price is kept so you
        can compare them, and the event keeps a stable address so saved events and shared links keep working.
      </p>
      <h2 id="deadlines">Deadlines</h2>
      <p>
        Deadlines come from registration fields when a source has them, or from phrases in the listing like "register by Nov 3". In that case
        we show the sentence we read. If a listing only says "registration required", we show that and never invent a countdown. New-resident
        deadlines (license, vehicle registration, voter registration) are quoted from official state websites and re-checked daily.
      </p>
      <h2 id="estimates">Estimates</h2>
      <p>Everything we estimate is labeled, comes with a range, and says how we got it.</p>
      <ul>
        <li><strong>Crowd size.</strong> Venue capacity times a typical fill for the ticket status. Without a known capacity, we use a typical range for that kind of event, at low confidence.</li>
        <li><strong>Tickets left.</strong> Shown only when a source reports spots (libraries and volunteer shifts often do), or as a labeled signal from resale listings. Listings aren't seats, and we say so.</li>
        <li><strong>Good for meeting people.</strong> Based on the kind of event (leagues and volunteering score high), whether it repeats, whether the listing says it's fine to come alone, and crowd size.</li>
        <li><strong>New openings.</strong> New liquor and business licenses are a signal that a place is opening, not a confirmed opening date, and are labeled that way.</li>
      </ul>
      <h2 id="ranking">How picks are chosen</h2>
      <p>
        "Picks this week" and your plan come from a ranking that weighs timing (soon, but not too soon to plan), how complete and reliable
        the listing is, whether it's good for meeting people, and variety, so one library or one category can't fill the page. If you save
        or open events, your browser uses that to adjust what it shows you. That learning happens on your device only. Every pick says why
        it's there.
      </p>
      <h2 id="limits">Known limits</h2>
      <ul>
        <li>Coverage differs by city. Each city page says how many sources it has and what it's strongest in.</li>
        <li>Many big-venue concerts need Ticketmaster, which isn't connected yet.</li>
        <li>Times are shown in the city's local time zone.</li>
      </ul>
      <p class="small muted">Data schema v{index.schema_version}.</p>
    </Page>
  );
}

export function Privacy() {
  return (
    <Page
      title="Privacy"
      lede="Short version: we don't collect anything about you. What you save stays in your browser."
      toc={[["device", "What stays on your device"], ["third", "Third parties"], ["links", "Links out"], ["changes", "Changes"]]}
    >
      <h2 id="device">What stays on your device</h2>
      <p>
        There are no accounts. Saved events, your plan preferences, your move date, the to-dos you check off, your theme choice, and what the
        ranking learns from the events you open and save are kept in your browser's local storage. They never leave your device unless you
        share a link yourself, and clearing your browser's site data deletes them.
      </p>
      <p>We don't use cookies, analytics, ad trackers or fingerprinting.</p>
      <h2 id="third">Third parties</h2>
      <ul>
        <li><strong>Hosting.</strong> The site is served by GitHub Pages. Like any web host, GitHub receives your IP address and browser details when you load a page; see GitHub's privacy statement.</li>
        <li><strong>Maps.</strong> Map tiles load from the OpenStreetMap Foundation's tile servers only when you open a map, under the OSMF privacy policy.</li>
        <li><strong>Fonts and code</strong> are served from this site. Nothing loads from ad or analytics networks.</li>
      </ul>
      <h2 id="links">Links out</h2>
      <p>When you follow a link to register or buy tickets, you're on the organizer's or seller's site and their privacy policy applies.</p>
      <h2 id="changes">Changes</h2>
      <p>If this ever changes, this page will say so first, with the date. Last updated October 16, 2026.</p>
    </Page>
  );
}
