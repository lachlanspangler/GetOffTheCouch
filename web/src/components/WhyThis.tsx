// "Why am I seeing this?": the ranking's own reasons in plain language, plus the privacy promise.
import { useApp } from "../lib/ctx";
import { whySeeingThis, type Profile, type Scored } from "../lib/recommend";

export function WhyThis({ s, profile }: { s: Scored; profile?: Profile | null }) {
  const { labels, feed } = useApp();
  const w = whySeeingThis(s, { profile: profile ?? null, labels, cityName: feed?.city_name });
  const items = [w.personal?.text, ...w.reasons.map((r) => r.text)].filter(Boolean) as string[];
  if (!items.length && !w.slot) return null;
  return (
    <details class="why-pop">
      <summary>Why this?</summary>
      <div>
        <p class="small" style={{ fontWeight: 600 }}>{w.headline}</p>
        <ul class="why-list small">
          {w.slot && <li>{w.slot}</li>}
          {items.map((t) => <li key={t}>{t}</li>)}
          {w.caveat && <li class="muted">{w.caveat.text}</li>}
        </ul>
        <p class="xs muted" style={{ marginTop: "6px" }}>{w.privacy}</p>
      </div>
    </details>
  );
}
