import type { Estimate, Event, Offer } from "./types";

const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const usd2 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-US");

export function money(n: number): string {
  return Number.isInteger(n) ? usd0.format(n) : usd2.format(n);
}

/** "Free", "$25", "$25–$80", or null when no source gave a price (we never guess). */
export function priceLabel(e: Event): string | null {
  const p = e.price;
  if (p.is_free) return "Free";
  const lo = p.min ?? null;
  const hi = p.max ?? null;
  if (lo == null && hi == null) return null;
  if (lo != null && hi != null && Math.round(lo) !== Math.round(hi)) return `${money(lo)}–${money(hi)}`;
  return money((lo ?? hi) as number);
}

export function offerPrice(o: Offer): string {
  const lo = o.price_min ?? null;
  const hi = o.price_max ?? null;
  if (lo == null && hi == null) return "—";
  if (lo != null && hi != null && lo !== hi) return `${money(lo)}–${money(hi)}`;
  return money((lo ?? hi) as number);
}

export function count(n: number): string {
  return num.format(Math.round(n));
}

/** "~1,200 (900–1,500)" — always the band, never false precision. */
export function estimateLabel(e: Estimate | null | undefined): string | null {
  if (!e) return null;
  return `~${count(e.mid)}`;
}

export function bandLabel(e: Estimate): string {
  return `${count(e.low)}–${count(e.high)}`;
}

export function confidenceWord(c: number): string {
  return c >= 0.7 ? "high" : c >= 0.45 ? "medium" : "low";
}

export const OFFER_KIND: Record<string, string> = {
  primary: "Face value",
  resale: "Resale",
  registration: "Register",
  rsvp: "RSVP",
  info: "Info",
};

export function availabilityLabel(a: string | undefined): string | null {
  switch (a) {
    case "sold_out": return "Sold out";
    case "few_left": return "Few left";
    case "limited": return "Limited";
    case "not_yet_on_sale": return "Not on sale yet";
    case "registration_open": return "Registration open";
    case "registration_closed": return "Registration closed";
    case "waitlist": return "Waitlist";
    case "cancelled": return "Cancelled";
    case "postponed": return "Postponed";
    case "on_sale": return "On sale";
    case "free_no_ticket": return "No ticket needed";
    default: return null;
  }
}

export function sourceName(id: string, names: Record<string, string>): string {
  return names[id] ?? id.replace(/_/g, " ");
}

/** "☀ 60°F" / "🌧 45°F · 70%" — compact NWS forecast label. */
export function weatherLabel(w: { short: string; temp_f?: number | null; precip_pct?: number | null } | null | undefined): string | null {
  if (!w) return null;
  const s = w.short.toLowerCase();
  const icon = /thunder/.test(s) ? "⛈" : /snow|flurr|sleet/.test(s) ? "🌨" : /rain|shower|drizzle/.test(s) ? "🌧" : /cloud|overcast/.test(s) ? "⛅" : /fog/.test(s) ? "🌫" : "☀";
  const t = w.temp_f != null ? ` ${Math.round(w.temp_f)}°F` : "";
  const p = w.precip_pct != null && w.precip_pct >= 30 ? ` · ${Math.round(w.precip_pct)}%` : "";
  return `${icon}${t}${p}`;
}

const STATES: Record<string, string> = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado", CT: "Connecticut", DE: "Delaware",
  DC: "Washington, DC", FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana", IA: "Iowa",
  KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota",
  MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey",
  NM: "New Mexico", NY: "New York", NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon",
  PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah",
  VT: "Vermont", VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
};

export function stateName(code: string): string {
  return STATES[code.toUpperCase()] ?? code;
}
