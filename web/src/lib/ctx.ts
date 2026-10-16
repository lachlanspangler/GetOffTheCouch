import { createContext } from "preact";
import { useContext } from "preact/hooks";
import type { Route } from "./router";
import type { CityFeed, Event, Index } from "./types";

export interface AppCtx {
  index: Index;
  feed: CityFeed | null;
  route: Route;
  go: (r: Partial<Route>, replace?: boolean) => void;
  labels: Record<string, string>;
  neighborhoods: Record<string, [number, number]>;
  sourceNames: Record<string, string>;
  byId: Map<string, Event>;
  saved: string[];
  toggleSave: (id: string) => void;
  now: Date;
  demo: boolean;
}

export const Ctx = createContext<AppCtx | null>(null);

export function useApp(): AppCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useApp outside provider");
  return c;
}
