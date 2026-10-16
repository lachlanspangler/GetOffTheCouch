// Hand-written types for files the pipeline writes outside CityFeed; CityFeed types are generated.
export type {
  CityFeed,
  Event,
  Offer,
  Estimate,
  Price,
  Registration,
  SourceStatus,
  Venue,
  PricePoint,
  FieldProvenance,
} from "./feed.generated";

export interface TaxonomyEntry {
  label: string;
  parent: string | null;
  icon: string;
}

export interface CitySummary {
  slug: string;
  name: string;
  state: string;
  timezone: string;
  center: [number, number];
  events: number;
  upcoming_7d: number;
  deadlines: number;
  sources_ok: number;
  sources_total: number;
  sources_disabled?: number;
  stale_sources: number;
}

export interface Index {
  schema_version: string;
  generated_at: string;
  taxonomy: Record<string, TaxonomyEntry>;
  tags: Record<string, string>;
  cities: CitySummary[];
}

export interface HealthUnit {
  city: string;
  source_id: string;
  name: string;
  state: string;
  last_success_at?: string;
  last_attempt_at?: string;
  sla_hours: number;
  stale: boolean;
  records: number;
  last_error?: string;
  reason?: string;
}

export interface HealthDoc {
  generated_at: string;
  units: HealthUnit[];
  log: { at: string; unit: string; level: string; kind: string; message: string }[];
}
