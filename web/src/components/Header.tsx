// Header, primary nav, tablet tabs and the mobile bottom bar (DESIGN.md §4.1).
import { useEffect, useState } from "preact/hooks";
import { useApp } from "../lib/ctx";
import { build, type View } from "../lib/router";
import { url } from "../lib/site";
import { CityPicker } from "./CityPicker";
import { Icon } from "./Icon";

export const NAV: { view: View; label: string; short: string; icon: string }[] = [
  { view: "feed", label: "Events", short: "Events", icon: "list" },
  { view: "deadlines", label: "Deadlines", short: "Deadlines", icon: "clock" },
  { view: "calendar", label: "Calendar", short: "Calendar", icon: "calendar" },
  { view: "map", label: "Map", short: "Map", icon: "map" },
  { view: "plan", label: "New in town", short: "New in town", icon: "compass" },
];

function current(view: View, eventId: string | null, v: View): "page" | undefined {
  return !eventId && view === v ? "page" : undefined;
}

export function Header({ deadlineCount }: { deadlineCount: number }) {
  const { route, saved } = useApp();
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(scrollY > 0);
    on();
    addEventListener("scroll", on, { passive: true });
    return () => removeEventListener("scroll", on);
  }, []);
  const city = route.city;
  const label = (t: (typeof NAV)[number]) => (
    <>
      {t.label}
      {t.view === "deadlines" && deadlineCount > 0 && <span class="count"> {deadlineCount}</span>}
    </>
  );
  return (
    <>
      <header class={`header ${scrolled ? "scrolled" : ""}`}>
        <div class="container header-inner">
          <a class="wordmark" href={url()} aria-label="Get Off the Couch, home">Get Off the Couch</a>
          <CityPicker />
          {city && (
            <nav class="nav-primary" aria-label="Primary">
              {NAV.map((t) => (
                <a key={t.view} href={build({ city, view: t.view })} aria-current={current(route.view, route.eventId, t.view)}>
                  {label(t)}
                </a>
              ))}
            </nav>
          )}
          <div class="header-right">
            {city && (
              <a class="header-saved" href={build({ city, view: "saved" })} aria-current={current(route.view, route.eventId, "saved")} aria-label={saved.length ? `Saved, ${saved.length}` : "Saved"}>
                <Icon name="bookmark" size={18} />
                <span class="lbl" aria-hidden="true">Saved{saved.length > 0 && <span class="count"> {saved.length}</span>}</span>
              </a>
            )}
          </div>
        </div>
        {city && (
          <nav class="tabs-md container" aria-label="Sections">
            {NAV.map((t) => (
              <a key={t.view} href={build({ city, view: t.view })} aria-current={current(route.view, route.eventId, t.view)}>
                {label(t)}
              </a>
            ))}
          </nav>
        )}
      </header>
      {city && (
        <nav class="bottom-nav" aria-label="Sections">
          {NAV.map((t) => (
            <a key={t.view} href={build({ city, view: t.view })} aria-current={current(route.view, route.eventId, t.view)}>
              <Icon name={t.icon} size={20} />
              {t.short}
            </a>
          ))}
        </nav>
      )}
    </>
  );
}
