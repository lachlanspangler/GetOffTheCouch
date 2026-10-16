// Golden rules (RANKING.md §3.3) as predicates, shared by the hard-fail tests and the eval report.

import type { Event } from "../types";
import { excluded } from "./candidates";
import { honest } from "./explain";
import { family, isLibrary, primarySource, wantsFamily } from "./profile";
import type { Profile, Scored } from "./types";

export interface RuleContext {
  now: Date;
  profile: Profile | null;
  surface: string;
  /** the scored pool the list was drawn from (rule 4 needs it) */
  pool?: Scored[];
}

export function violations(list: Scored[], ctx: RuleContext): string[] {
  const out: string[] = [];
  const top = list.slice(0, 10);
  const ev = (s: Scored) => s.event;
  const name = (e: Event) => `${e.title} (${e.id})`;
  for (const s of list) if (excluded(ev(s), ctx.now)) out.push(`1 excluded item shown: ${name(ev(s))}`);
  if (!wantsFamily(ctx.profile)) for (const s of top) if ((ev(s).tags ?? []).includes("kids_teens")) out.push(`2 kids item for adults: ${name(ev(s))}`);
  const count = (key: (e: Event) => string | null | undefined) => {
    const m = new Map<string, number>();
    for (const s of top) {
      const k = key(ev(s));
      if (k) m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  };
  for (const [k, n] of count(primarySource)) if (n > 2) out.push(`3 source ${k} ×${n} in top 10`);
  for (const [k, n] of count((e) => e.series_id)) if (n > 1) out.push(`3 series ${k} ×${n}`);
  for (const [k, n] of count((e) => e.rank?.group)) if (n > 1) out.push(`3 multi-site group ${k} ×${n}`);
  if (ctx.surface === "highlights" && top.filter((s) => isLibrary(ev(s))).length > 1) out.push("3 more than one library event in Highlights");
  if (ctx.pool) {
    const poolFams = new Set(ctx.pool.filter((s) => (s.rel ?? 0) >= 0.3 && !(s.event.tags ?? []).includes("kids_teens")).map((s) => family(s.event.category)));
    const fams = new Set(top.map((s) => family(ev(s).category)));
    if (top.length >= 10 && poolFams.size >= 3 && fams.size < 3) out.push(`4 only ${fams.size} families in top 10`);
  }
  for (const s of top) if ((ev(s).rank?.lowq ?? 0) >= 0.7) out.push(`5 low-quality item: ${name(ev(s))}`);
  for (const s of list) for (const p of honest(s)) out.push(`6 ${p}`);
  return out;
}
