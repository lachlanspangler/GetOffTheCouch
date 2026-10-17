// Rarely visited pages (about/methodology/privacy, the plan wizard, the status page) load on demand so the entry
// bundle stays inside its budget. The pre-renderer registers them eagerly (entry-server.tsx), and main.tsx preloads
// the one a pre-rendered page needs before hydrating, so SSR and hydration still render them synchronously.
import type { FunctionComponent } from "preact";
import { useEffect, useState } from "preact/hooks";

/* eslint-disable @typescript-eslint/no-explicit-any */
type Any = FunctionComponent<any>;
export type LazyName = "about" | "methodology" | "privacy" | "plan" | "health";

const registry: Partial<Record<LazyName, Any>> = {};
const loaders: Record<LazyName, () => Promise<Partial<Record<LazyName, Any>>>> = {
  about: () => import("../views/About").then((m) => ({ about: m.About, methodology: m.Methodology, privacy: m.Privacy })),
  methodology: () => loaders.about(),
  privacy: () => loaders.about(),
  plan: () => import("../views/Plan").then((m) => ({ plan: m.Plan })),
  health: () => import("../views/Health").then((m) => ({ health: m.Health })),
};

export function registerViews(views: Partial<Record<LazyName, Any>>): void {
  Object.assign(registry, views);
}

export async function preloadView(name: string): Promise<void> {
  if (name in loaders && !registry[name as LazyName]) registerViews(await loaders[name as LazyName]());
}

export function useView(name: LazyName): Any | null {
  const [, bump] = useState(0);
  const C = registry[name] ?? null;
  useEffect(() => {
    if (!C) void preloadView(name).then(() => bump((n) => n + 1));
  }, [name, C]);
  return C;
}
