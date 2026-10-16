// Tiny reactive localStorage store (saved events, profile, reminders). Private: never leaves the device.
import { useEffect, useState } from "preact/hooks";

const PREFIX = "gotc:";

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? ({ ...fallback, ...JSON.parse(raw) } as T) : fallback;
  } catch {
    return fallback;
  }
}

export function loadRaw<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

const listeners = new Map<string, Set<() => void>>();

/** True while hydrating a pre-rendered page: the first render must match the server (no stored values yet). */
export const hydration = { active: false };

export function save<T>(key: string, value: T): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    /* storage full or disabled: the app still works, just without persistence */
  }
  listeners.get(key)?.forEach((fn) => fn());
}

export function usePersistent<T>(key: string, fallback: T, merge = false): [T, (v: T) => void] {
  const read = () => (merge ? load(key, fallback) : loadRaw(key, fallback));
  const [value, setValue] = useState<T>(() => (hydration.active ? fallback : read()));
  useEffect(() => {
    const fn = () => setValue(read());
    fn(); // after hydration, swap the server's defaults for this device's stored values
    const set = listeners.get(key) ?? new Set();
    set.add(fn);
    listeners.set(key, set);
    return () => set.delete(fn);
  }, [key]);
  return [value, (v: T) => save(key, v)];
}
