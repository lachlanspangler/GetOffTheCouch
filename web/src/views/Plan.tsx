// "New in town": a short wizard, then a first-month plan where every pick says why (DESIGN.md §4.12).
import { useMemo, useState } from "preact/hooks";
import { CompactRow } from "../components/EventRow";
import { Icon } from "../components/Icon";
import { StarterPack } from "../components/StarterPack";
import { ART_HUE, familyOf } from "../lib/art";
import { children, families } from "../lib/categories";
import { useApp } from "../lib/ctx";
import { calendar, download } from "../lib/ics";
import { buildPlan, DEFAULT_PROFILE, GOALS, learnedSummary, resetAffinity, type Goal, type Profile, type Scored, type Slot } from "../lib/recommend";
import { absolute } from "../lib/site";
import { usePersistent } from "../lib/store";
import { fmtDay } from "../lib/time";
import type { Event } from "../lib/types";
import { vibes } from "../lib/vibes";
import { share } from "./EventPage";

const SLOTS: Record<Slot, string> = { weeknights: "Weeknights", weekends: "Weekends", daytime: "Weekday daytime" };
const BUDGET = { free: "Free only", cheap: "Under about $30", any: "Whatever's good" } as const;

function Wizard({ initial, onDone, events }: { initial: Profile; onDone: (p: Profile) => void; events: Event[] }) {
  const { index, feed } = useApp();
  const [p, setP] = useState<Profile>(initial);
  const [step, setStep] = useState(0);
  const fams = families(index.taxonomy);
  const toggle = <T,>(arr: T[], v: T): T[] => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  const steps = [
    { title: "What do you like to do?", help: "Pick a few. You can change these any time." },
    { title: "What do you want out of it?", help: "This decides what we put first. Pick any that fit." },
    { title: "Where and when?", help: "Both optional. We use your move date to work out the state deadlines." },
  ];
  const last = step === steps.length - 1;
  return (
    <div class="container">
      <div class="wizard">
        <p class="progress-text">Step {step + 1} of {steps.length + 1}</p>
        <div class="track" role="progressbar" aria-label="Plan setup" aria-valuemin={1} aria-valuemax={steps.length + 1} aria-valuenow={step + 1}>
          <i style={{ width: `${((step + 1) / (steps.length + 1)) * 100}%` }} />
        </div>
        <h1>{steps[step].title}</h1>
        <p class="help">{steps[step].help}</p>
        <div class="body">
          {step === 0 && (
            <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
              <legend class="sr-only">Interests</legend>
              <div class="pick-grid">
                {fams.map((f) => (
                  <label class="pick" key={f}>
                    <input type="checkbox" checked={p.interests.includes(f)} onChange={() => setP({ ...p, interests: toggle(p.interests, f) })} />
                    <span class="lbl"><span class="swatch" style={{ "--art-h": ART_HUE[familyOf(f)] }} aria-hidden="true" />{index.taxonomy[f].label}</span>
                    <span class="ex">{children(index.taxonomy, f).filter((c) => !/furry/i.test(index.taxonomy[c].label)).slice(0, 3).map((c) => index.taxonomy[c].label).join(", ")}</span>
                    <Icon name="check" size={16} class="tick" />
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          {step === 1 && (
            <>
              <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                <legend class="label small" style={{ fontWeight: 600, marginBottom: "8px" }}>Goals</legend>
                <div class="pick-grid">
                  {(Object.keys(GOALS) as Goal[]).map((g) => (
                    <label class="pick" key={g}>
                      <input type="checkbox" checked={p.goals.includes(g)} onChange={() => setP({ ...p, goals: toggle(p.goals, g) })} />
                      <span class="lbl">{GOALS[g].label}</span>
                      <Icon name="check" size={16} class="tick" />
                    </label>
                  ))}
                </div>
              </fieldset>
              <label class="check">
                <input type="checkbox" checked={p.solo} onChange={() => setP({ ...p, solo: !p.solo })} /> I'll mostly be going on my own
              </label>
              <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                <legend class="label small" style={{ fontWeight: 600, marginBottom: "8px" }}>Budget</legend>
                <div class="seg" role="radiogroup" aria-label="Budget" style={{ maxWidth: "460px" }}>
                  {(Object.keys(BUDGET) as (keyof typeof BUDGET)[]).map((b) => (
                    <button key={b} role="radio" aria-checked={p.budget === b} onClick={() => setP({ ...p, budget: b })}>{BUDGET[b]}</button>
                  ))}
                </div>
              </fieldset>
              <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                <legend class="label small" style={{ fontWeight: 600, marginBottom: "4px" }}>Usually free</legend>
                {(Object.keys(SLOTS) as Slot[]).map((s) => (
                  <label class="check" key={s}>
                    <input type="checkbox" checked={p.times.includes(s)} onChange={() => setP({ ...p, times: toggle(p.times, s) })} /> {SLOTS[s]}
                  </label>
                ))}
              </fieldset>
            </>
          )}
          {step === 2 && (
            <>
              <label class="field">
                <span class="label">When did you move (or when will you)?</span>
                <input class="input" type="date" value={p.startDate ?? ""} onInput={(e) => setP({ ...p, startDate: (e.target as HTMLInputElement).value || null })} style={{ maxWidth: "240px" }} />
                <span class="help">Leave it blank if you're already settled in. It stays on this device.</span>
              </label>
              {(feed?.neighborhoods?.length ?? 0) > 0 && (
                <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
                  <legend class="label small" style={{ fontWeight: 600, marginBottom: "8px" }}>Where will you spend most of your time?</legend>
                  <div class="pick-grid">
                    {vibes(events, feed!.neighborhoods!).slice(0, 9).map((v) => (
                      <label class="pick" key={v.name}>
                        <input type="radio" name="hood" checked={p.neighborhood === v.name} onChange={() => setP({ ...p, neighborhood: v.name })} />
                        <span class="lbl">{v.name}</span>
                        <span class="ex">{v.total} upcoming nearby{v.top[0] ? `, mostly ${(index.taxonomy[v.top[0].family]?.label ?? v.top[0].family).toLowerCase()}` : ""}</span>
                        <Icon name="check" size={16} class="tick" />
                      </label>
                    ))}
                  </div>
                  {p.neighborhood && <button class="link-btn small" style={{ marginTop: "8px" }} onClick={() => setP({ ...p, neighborhood: null })}>No preference</button>}
                </fieldset>
              )}
            </>
          )}
        </div>
        <div class="wizard-nav">
          {step > 0 ? <button class="btn btn-quiet" onClick={() => setStep(step - 1)}>Back</button> : <span />}
          {last ? (
            <button class="btn btn-lg" onClick={() => onDone(p)}>Make my plan</button>
          ) : (
            <button class="btn btn-lg" onClick={() => setStep(step + 1)} aria-disabled={step === 0 && !p.interests.length} disabled={step === 0 && !p.interests.length}>
              Continue
            </button>
          )}
        </div>
        {step === 0 && !p.interests.length && <p class="small muted" style={{ textAlign: "right", marginTop: "8px" }}>Pick at least one to continue.</p>}
      </div>
    </div>
  );
}

function PickList({ picks, reasonPrefix }: { picks: Scored[]; reasonPrefix?: (s: Scored) => string | null }) {
  return (
    <ul class="rows">
      {picks.map((s) => {
        const reasons = [reasonPrefix?.(s), ...s.reasons.filter((r) => r.weight > 0).map((r) => r.text)].filter(Boolean).slice(0, 2);
        return <CompactRow key={s.event.id} e={s.event} time={fmtDay(s.event.start, s.event.timezone)} sub={reasons.join(" · ")} />;
      })}
    </ul>
  );
}

export function Plan({ events }: { events: Event[] }) {
  const { feed, labels, neighborhoods, now } = useApp();
  const [profile, setProfile] = usePersistent<Profile | null>(`profile:${feed?.city ?? "_"}`, null);
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const plan = useMemo(() => (profile && profile.interests.length ? buildPlan(events, profile, labels, neighborhoods, now) : null), [events, profile, now]);
  if (!feed) return null;
  if (!profile || !profile.interests.length || editing) {
    return <Wizard events={events} initial={profile ?? DEFAULT_PROFILE} onDone={(p) => { setProfile(p); setEditing(false); scrollTo(0, 0); }} />;
  }
  if (!plan) return null;
  const all = [...plan.deadlines, ...plan.habits, ...plan.weeks.flatMap((w) => w.picks)].map((s) => s.event);
  const uniq = [...new Map(all.map((e) => [e.id, e])).values()];
  const move = profile.startDate ? new Date(`${profile.startDate}T12:00:00`) : null;
  return (
    <div class="container narrow">
      <header class="page-head inner">
        <h1>Your first month in {feed.city_name}</h1>
        <p class="lede">
          Chosen for {profile.interests.map((i) => labels[i] ?? i).slice(0, 3).join(", ").toLowerCase()}{profile.interests.length > 3 ? " and more" : ""}.
          {move && <> You {move > now ? "arrive" : "moved"} {fmtDay(move.toISOString(), feed.timezone)}.</>}
        </p>
        <div class="actions row">
          <button class="btn btn-secondary" onClick={() => download(`${feed.city}-first-month.ics`, calendar(uniq, { name: `My first month in ${feed.city_name}` }))}>
            <Icon name="calendarPlus" size={16} /> Add the plan to your calendar
          </button>
          <button class="btn btn-quiet" onClick={async () => setMsg(await share(`My first month in ${feed.city_name}`, absolute(`${feed.city}/saved/?ids=${uniq.map((e) => e.id).join(",")}`)))}>
            <Icon name="share" size={16} /> {msg ?? "Share"}
          </button>
          <button class="btn btn-quiet" onClick={() => setEditing(true)}>Change answers</button>
        </div>
      </header>
      {plan.deadlines.length > 0 && (
        <section class="plan-sec" aria-labelledby="p-dl">
          <h2 id="p-dl">Sign up soon</h2>
          <p>Registration closes for these before your first month is out.</p>
          <PickList picks={plan.deadlines} />
        </section>
      )}
      {plan.habits.length > 0 && (
        <section class="plan-sec" aria-labelledby="p-hab">
          <h2 id="p-hab">Pick a weekly habit</h2>
          <p>Going to the same thing every week is how strangers become friends. These repeat and are good for meeting people.</p>
          <PickList picks={plan.habits} reasonPrefix={(s) => s.event.recurrence ?? "Repeats"} />
        </section>
      )}
      {plan.weeks.map((w, i) => (
        <section key={w.from} class="plan-sec" aria-labelledby={`p-w${i}`}>
          <h2 id={`p-w${i}`}>{i === 0 ? "This week" : `Week of ${fmtDay(w.from, feed.timezone)}`}</h2>
          {w.picks.length ? <PickList picks={w.picks} /> : <p>Nothing that fits yet. Listings update every few hours.</p>}
        </section>
      ))}
      {plan.openings.length > 0 && (
        <section class="plan-sec" aria-labelledby="p-new">
          <h2 id="p-new">New places to try</h2>
          <p>From new liquor and business licenses: a sign a place is opening, not a confirmed date.</p>
          <PickList picks={plan.openings} />
        </section>
      )}
      <div class="section"><StarterPack /></div>
      <Learned />
    </div>
  );
}

/** What the ranking has learned from this device's saves and clicks, with a way to forget it. */
function Learned() {
  const { labels } = useApp();
  const [, bump] = useState(0);
  const rows = learnedSummary(labels).filter((r) => Math.abs(r.lean) >= 0.05).slice(0, 8);
  return (
    <section class="plan-sec" aria-labelledby="p-learn">
      <h2 id="p-learn">What we've learned on this device</h2>
      <p>Picks adjust to what you save, open and add to your calendar. This stays in your browser and is never sent anywhere.</p>
      {rows.length ? (
        <>
          <ul class="why-list">{rows.map((r) => <li key={r.key}>{r.text}</li>)}</ul>
          <button class="btn btn-quiet btn-sm" style={{ marginTop: "12px" }} onClick={() => { resetAffinity(); bump((n) => n + 1); }}>Forget all of this</button>
        </>
      ) : (
        <p class="small muted">Nothing yet. Save or open a few events and your picks will start to lean your way.</p>
      )}
    </section>
  );
}
