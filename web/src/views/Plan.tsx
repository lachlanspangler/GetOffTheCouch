// "New in town": pick interests → a personalized first-30-days plan that explains every pick.
import { useMemo, useState } from "preact/hooks";
import { EventCard } from "../components/EventCard";
import { StarterPack } from "../components/StarterPack";
import { Icon } from "../components/Icon";
import { useApp } from "../lib/ctx";
import { catIcon, children, families, hue } from "../lib/categories";
import { calendar, download } from "../lib/ics";
import { buildPlan, DEFAULT_PROFILE, GOALS, type Goal, type Profile, type Slot } from "../lib/recommend";
import { usePersistent } from "../lib/store";
import { fmtDay } from "../lib/time";
import type { Event } from "../lib/types";

const SLOTS: Record<Slot, string> = { weeknights: "Weeknights", weekends: "Weekends", daytime: "Weekday daytime" };

function Onboarding({ initial, onDone }: { initial: Profile; onDone: (p: Profile) => void }) {
  const { index, feed } = useApp();
  const [p, setP] = useState<Profile>(initial);
  const [step, setStep] = useState(0);
  const fams = families(index.taxonomy);
  const toggle = <T,>(arr: T[], v: T): T[] => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  const steps = ["What are you into?", "What do you want out of it?", "Budget & timing", "Where & when"];
  return (
    <div class="onboard">
      <div class="onboard-progress" role="progressbar" aria-label="Onboarding progress" aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={step + 1} aria-valuetext={`Step ${step + 1} of ${steps.length}`}>
        {steps.map((s, i) => <span key={s} class={i <= step ? "on" : ""} />)}
      </div>
      <h2>{steps[step]}</h2>
      {step === 0 && (
        <>
          <p class="muted">Pick as many as you like. Tap a big tile for everything in it, or the small chips to get specific.</p>
          <div class="interest-grid">
            {fams.map((f) => {
              const on = p.interests.includes(f);
              return (
                <div key={f} class={`interest ${on ? "on" : ""}`} style={{ "--h": hue(f) }}>
                  <button class="interest-main" aria-pressed={on} onClick={() => setP({ ...p, interests: toggle(p.interests, f) })}>
                    <Icon name={catIcon(f, index.taxonomy)} size={22} />
                    <span>{index.taxonomy[f].label}</span>
                  </button>
                  <div class="interest-kids">
                    {children(index.taxonomy, f).slice(0, 8).map((c) => (
                      <button
                        key={c}
                        class={`chip tiny ${p.interests.includes(c) ? "on" : ""}`}
                        aria-pressed={p.interests.includes(c)}
                        onClick={() => setP({ ...p, interests: toggle(p.interests, c) })}
                      >
                        {index.taxonomy[c].label}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
      {step === 1 && (
        <div class="chips big">
          {(Object.keys(GOALS) as Goal[]).map((g) => (
            <button key={g} class={`chip ${p.goals.includes(g) ? "on" : ""}`} aria-pressed={p.goals.includes(g)} onClick={() => setP({ ...p, goals: toggle(p.goals, g) })}>
              {GOALS[g].label}
            </button>
          ))}
          <label class="check">
            <input type="checkbox" checked={p.solo} onChange={() => setP({ ...p, solo: !p.solo })} /> I'll mostly be going solo
          </label>
        </div>
      )}
      {step === 2 && (
        <div class="stack">
          <div class="seg" role="radiogroup" aria-label="Budget">
            {(["free", "cheap", "any"] as const).map((b) => (
              <button key={b} role="radio" aria-checked={p.budget === b} class={p.budget === b ? "on" : ""} onClick={() => setP({ ...p, budget: b })}>
                {b === "free" ? "Free stuff only" : b === "cheap" ? "Under ~$30" : "Whatever's good"}
              </button>
            ))}
          </div>
          <div class="chips big">
            {(Object.keys(SLOTS) as Slot[]).map((s) => (
              <button key={s} class={`chip ${p.times.includes(s) ? "on" : ""}`} aria-pressed={p.times.includes(s)} onClick={() => setP({ ...p, times: toggle(p.times, s) })}>
                {SLOTS[s]}
              </button>
            ))}
          </div>
        </div>
      )}
      {step === 3 && (
        <div class="stack">
          <label class="field">
            <span>Where will you live (or hang out)?</span>
            <select value={p.neighborhood ?? ""} onChange={(e) => setP({ ...p, neighborhood: (e.target as HTMLSelectElement).value || null })}>
              <option value="">Not sure yet</option>
              {feed?.neighborhoods?.map((n) => <option key={n.name} value={n.name}>{n.name}</option>)}
            </select>
          </label>
          <label class="field">
            <span>When do you arrive? (leave blank if you're already here)</span>
            <input type="date" value={p.startDate ?? ""} onInput={(e) => setP({ ...p, startDate: (e.target as HTMLInputElement).value || null })} />
          </label>
        </div>
      )}
      <div class="onboard-nav">
        {step > 0 && <button class="btn btn-ghost" onClick={() => setStep(step - 1)}>Back</button>}
        {step < steps.length - 1 ? (
          <button class="btn" onClick={() => setStep(step + 1)} disabled={step === 0 && p.interests.length === 0}>
            Next
          </button>
        ) : (
          <button class="btn" onClick={() => onDone(p)}>
            <Icon name="sparkles" size={16} /> Build my first month
          </button>
        )}
      </div>
    </div>
  );
}

export function Plan({ events }: { events: Event[] }) {
  const { feed, labels, neighborhoods, now } = useApp();
  const [profile, setProfile] = usePersistent<Profile | null>(`profile:${feed?.city ?? "_"}`, null);
  const [editing, setEditing] = useState(false);
  const plan = useMemo(
    () => (profile ? buildPlan(events, profile, labels, neighborhoods, now) : null),
    [events, profile, now],
  );
  if (!feed) return null;
  if (!profile || editing) {
    return (
      <Onboarding
        initial={profile ?? DEFAULT_PROFILE}
        onDone={(p) => {
          setProfile(p);
          setEditing(false);
        }}
      />
    );
  }
  if (!plan) return null;
  const all = [...plan.weeks.flatMap((w) => w.picks.map((s) => s.event)), ...plan.deadlines.map((s) => s.event)];
  const uniq = [...new Map(all.map((e) => [e.id, e])).values()];
  const total = plan.weeks.reduce((n, w) => n + w.picks.length, 0);
  return (
    <div class="plan">
      <header class="view-head">
        <div>
          <h2>Your first 30 days in {feed.city_name}</h2>
          <p class="muted">
            {total} picks chosen for {profile.interests.map((i) => labels[i] ?? i).slice(0, 4).join(", ")}
            {profile.interests.length > 4 ? "…" : ""}. Every pick says why.
          </p>
        </div>
        <div class="row">
          <button class="btn btn-ghost" onClick={() => setEditing(true)}>Edit preferences</button>
          {uniq.length > 0 && (
            <button class="btn" onClick={() => download(`${feed.city}-first-30-days.ics`, calendar(uniq, { name: `My first month in ${feed.city_name}` }))}>
              <Icon name="calendar" size={16} /> Add plan to calendar
            </button>
          )}
        </div>
      </header>
      <StarterPack />
      {plan.deadlines.length > 0 && (
        <section class="plan-block act-now">
          <h3><Icon name="clock" size={18} /> Act now: deadlines for things you'd like</h3>
          <div class="grid">
            {plan.deadlines.map((s) => <EventCard key={s.event.id} e={s.event} why={s.reasons.filter((r) => r.weight > 0).map((r) => r.text)} />)}
          </div>
        </section>
      )}
      {plan.weeks.map((w) => (
        <section key={w.from} class="plan-block">
          <h3>
            {w.label} <span class="muted">· from {fmtDay(w.from, feed.timezone)}</span>
          </h3>
          {w.picks.length ? (
            <div class="grid">
              {w.picks.map((s) => <EventCard key={s.event.id} e={s.event} why={s.reasons.filter((r) => r.weight > 0).map((r) => r.text)} />)}
            </div>
          ) : (
            <p class="muted">Nothing great matches yet for this week. Data refreshes hourly, so check back.</p>
          )}
        </section>
      ))}
      {plan.openings.length > 0 && (
        <section class="plan-block">
          <h3><Icon name="store" size={18} /> New spots to try</h3>
          <div class="grid">
            {plan.openings.map((s) => <EventCard key={s.event.id} e={s.event} />)}
          </div>
        </section>
      )}
    </div>
  );
}
