// Drop the legacy monolithic city files from the Pages artifact (ADR-0009 amendment, 2026-11-02).
// Browsers load week shards via cities/<slug>/manifest.json; the whole-feed files stay in web/public/data for the
// build-time scripts (share cards, pre-render) and the contract tests, but shipping them doubled dist/data and pushed
// the artifact past GitHub Pages' 1 GB limit once Ticketmaster was keyed (NYC alone: 42 MB + 13 MB).
//   node scripts/prune-dist.mjs
import { existsSync, readdirSync, rmSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const cities = join(resolve("dist"), "data", "cities");
let removed = 0;
let bytes = 0;
if (existsSync(cities)) {
  for (const slug of readdirSync(cities).filter((d) => existsSync(join(cities, d, "manifest.json")))) {
    for (const f of [`${slug}.json`, `${slug}.details.json`]) {
      const p = join(cities, f);
      if (existsSync(p)) {
        bytes += statSync(p).size;
        rmSync(p);
        removed++;
      }
    }
  }
}
console.log(`prune-dist: removed ${removed} legacy city files (${(bytes / 1e6).toFixed(1)} MB); sharded cities load week shards`);
