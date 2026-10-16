// Category presentation: one hue per top-level family, used for chips, card accents and map pins.
import type { TaxonomyEntry } from "./types";

export const FAMILY_HUE: Record<string, number> = {
  music: 280,
  sports_league: 145,
  nightlife: 320,
  community: 30,
  food_drink: 15,
  volunteer: 350,
  niche: 260,
  trivia_games: 200,
  fitness: 165,
  outdoors: 110,
  arts: 45,
  sports_watch: 220,
  family: 55,
  learning: 190,
  other: 230,
};

export function family(id: string): string {
  return id.split(".")[0];
}

export function hue(id: string): number {
  return FAMILY_HUE[family(id)] ?? 230;
}

export function catLabel(id: string, tax: Record<string, TaxonomyEntry>): string {
  return tax[id]?.label ?? tax[family(id)]?.label ?? id;
}

export function catIcon(id: string, tax: Record<string, TaxonomyEntry>): string {
  return tax[id]?.icon ?? tax[family(id)]?.icon ?? "dot";
}

export function families(tax: Record<string, TaxonomyEntry>): string[] {
  return Object.keys(tax).filter((k) => !tax[k].parent && k !== "other");
}

export function children(tax: Record<string, TaxonomyEntry>, fam: string): string[] {
  return Object.keys(tax).filter((k) => tax[k].parent === fam);
}
