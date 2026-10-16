# GetOffTheCouch design system (research + spec)

Status: proposal, 2026-10-16. Scope: the static Preact site in `web/`. This spec replaces the token block and the visual language in `web/src/styles/app.css`. It does not change the data contract, routes or features.

Target feel: an established, trusted local guide. Think the calm of Airbnb and Resy listings, the editorial confidence of The Infatuation and Time Out, the restraint of Apple, Linear and Stripe. No gamification: no badges-as-rewards, streaks, confetti, notification bubbles, tilted icons, or glow.

How this was researched:
- Fetched Linear's redesign writeup ("How we redesigned the Linear UI") and Stripe's "Designing accessible color systems".
- Fetched the Geist license (confirmed SIL OFL 1.1, no Reserved Font Name) and the Inter release notes (4.0 added an `opsz` axis and Inter Display).
- Downloaded Inter and Newsreader from `google/fonts` (both OFL), subset them locally with fontTools and measured the woff2 sizes. Every KB figure below is measured, not guessed.
- Computed the fallback metric overrides against the macOS Arial, Georgia and Times New Roman files with the capsize letter-frequency method. My Inter/Arial result matches the published next/font values (107.4% / 90.2% / 22.48%), which validates the method.
- Checked every color pair in §3 with the WCAG 2.x relative-luminance formula. The ratios are printed next to each pair.
- Read the other sites' public listing pages where possible (Time Out returned 404). Otherwise I relied on well-documented public patterns (Airbnb Cereal, Resy, Apple HIG) and marked them as such.

---

## 0. What the reference sites actually do (the patterns we're borrowing)

| Site | Pattern worth copying | How it maps to us |
|---|---|---|
| **Airbnb** | One brand accent (Rausch) used almost only for the primary CTA and the selected state. Everything else is near-black text on white with 1px #DDD hairlines. Listing cards have no border and no shadow; the image does the work. Meta is gray text with "·" separators. | One accent (Ember) used for the primary CTA, the selected state and focus only. Card meta is plain text with `·`, not pills. |
| **Resy** | Dense, scannable list rows: name, then cuisine · neighborhood · price as one gray line, then time-slot buttons. Rows are separated by dividers, not boxed in cards. | Feed becomes **dividered list rows grouped by day**, not a 3-column grid of boxed cards. |
| **The Infatuation** | Each card is image, title, category link, neighborhood link and a one-sentence blurb. A rating appears on some cards only. Sections like "Just Published" and "Best Of" use editorial headlines. Serif display, sans UI. | Serif display for page and section headlines. One plain line of "why it's here" on featured cards only. Neighborhood is a first-class label. |
| **Time Out** | Numbered editorial lists ("The best things to do this weekend"), a bold date line, short paragraphs, price in plain text. | City landing gets an editorial "This weekend" list with a written date line ("Fri, Oct 16 – Sun, Oct 18"). |
| **Linear** | Moved themes to LCH. One generator makes light and dark from three inputs (base, accent, contrast). Used less blue in the chrome "for a more neutral, timeless look". Inter Display for headings, Inter for text. Dense but aligned. | Neutrals are warm "sand" with very low chroma. Dark mode is generated from the same ramp. Category art uses OKLCH so hues have equal perceived lightness. |
| **Stripe** | Perceptual color space (CIELAB). Every hue follows the same lightness curve, so "any two colors ≥5 levels apart pass 4.5:1 and ≥4 levels pass 3:1". Default text passes on white and on the lightest tint of any hue. | The ramps follow the same rule: text uses step ≥600 on ≤100 backgrounds. Every pair used is listed with its ratio (§3.4). |
| **Apple** | Big confident type, lots of whitespace, almost no ornament. Motion only explains spatial change. Respects reduced motion. | Motion budget §3.9: no hover lifts, no spinners longer than 300ms before a skeleton. |

The common denominator: **hierarchy comes from typography and whitespace, not from color fills.** Color is rare, which is why it reads as meaningful. The current site does the opposite (§7).

---

## 1. Brand

### 1.1 Name treatment
- **Name in prose:** "GetOffTheCouch" stays the product/domain name. In running text and the wordmark, write it as **Get Off the Couch** (title case, lowercase "the"). In URLs and code, keep `getoffthecouch`.
- **Wordmark:** "Get Off the Couch" set in Newsreader Medium (500), opsz 36, `letter-spacing: -0.01em`, color `--color-text`. Desktop 22px, mobile 19px. No box, no rotation, no shadow, no gradient.
- **Tagline:** retire "ur city made easy" in the UI. Txt-speak reads cutesy and undercuts trust on a page that also tells you a DMV deadline. Replacement: **"Your city, made easy."** It keeps the meaning and is plain-spoken. Use it in `<title>`, meta description and the home hero kicker only, not under the logo in the header. (CLAUDE.md can keep the old line as internal shorthand.)
- **`<title>` pattern:** `{Page} · {City} · Get Off the Couch` (e.g. `This weekend · Chicago · Get Off the Couch`). Home: `Get Off the Couch · Your city, made easy`.

### 1.2 Logo direction
- **Mark:** a monoline **open doorway**: an arch, 2px stroke on a 24px grid, with a short horizontal threshold line. It means "out the door", not "couch". The current couch glyph says "stay on the couch", which is the opposite of the product. Used for the favicon, the app-icon and the social avatar only. The header uses the wordmark alone.
- **Favicon:** the arch in `#FFFFFF` on a `#1F1D1A` rounded square (radius 22% of size). It stays legible at 16px and doesn't vibrate like the orange tile does. `theme-color`: `#FCFBF8` light / `#151412` dark (two `<meta name="theme-color" media=...>` tags).
- **Don'ts:** no tilt, no drop shadow, no accent-filled tile in the header, no emoji, no mascot.

### 1.3 Voice and tone
We sound like **a friend who has lived here ten years and also reads the fine print.** We're warm, local, specific and calm. We say what we know and how we know it. We never hype, never guilt, and never fake urgency.

Rules:
1. **Plain verbs, sentence case.** Buttons say what happens: "Register on Eventbrite", not "Let's go!".
2. **Specific beats clever.** "Closes Thu, Oct 22" beats "Don't miss out!".
3. **Say where the data came from** when it matters: "From the Chicago Park District, checked 3 hours ago."
4. **Never invent urgency.** Only show a countdown when a published deadline exists. Only use the critical color when ≤48 hours are left.
5. **No txt-speak, no exclamation marks, no emoji in UI chrome.** One exclamation mark is allowed per product, and we haven't spent it.
6. **Second person, present tense.** "You can still sign up", not "Users may register".
7. **Numbers as numerals,** with the en dash for ranges ("$12–$20", "7–10 PM"). Use "Free" (capitalized) as a price.

| Context | Good | Bad (and why) |
|---|---|---|
| Primary CTA, ticketed | **Get tickets on Ticketmaster** ↗ | "Tickets!!" (hype); "Buy now" (we don't sell anything) |
| Primary CTA, league | **Register with Chicago Park District** ↗ | "Join the fun" (vague) |
| Save | **Save** / **Saved** | "Heart it", "Add to my vibes" (cutesy) |
| Filter reset | **Clear filters** | "Start over 🙃" |
| Results count | **1,593 events** | "1593 things" (no thousands separator; "things" sounds flippant) |
| Empty feed (filters) | **Nothing matches these filters.** Try a wider date range or remove "Free only". [Clear filters] | "Uh oh! Looks like the couch wins today 🛋️" |
| Empty saved | **Nothing saved yet.** Tap Save on any event and it'll show up here, on this device only. | "Your list is lonely!" |
| Empty deadlines | **No sign-up deadlines in the next 60 days.** We check 12 sources daily; new leagues usually post 4–6 weeks before a season. | A big orange check mark plus "No open deadlines right now" with no context |
| Error, data load | **We couldn't load Chicago's events.** Your connection may have dropped. [Try again] | "Oops! Something went wrong." (says nothing) |
| Stale source | **Last updated 3 days ago.** The Park District site hasn't responded since Tuesday; showing the last listings we got. | "⚠ stale" (jargon, alarm) |
| Deadline ≤48h | **Registration closes tomorrow, 11:59 PM** | "HURRY! 1 day left!!" |
| Deadline 3–14 days | **Registration closes Thu, Oct 22** | "5 days left to register" (makes the reader do math against a fuzzy "day") |
| Derived deadline (no published date) | **Registration required. Spots fill as people sign up.** | Any countdown at all (it would be fabricated) |
| Spots | **4 of 24 spots left** (shown only when ≤25% remain) | "🔥 Almost gone" |
| Price trend | **Lowest price down 18% since Monday** (detail page) | "↓ 18% this week" as a red/green chip on the card |
| Social | **Good for meeting people**: a category with a mixer format, solo-friendly | "Meet people!" in purple |
| Onboarding step | **What do you like to do?** Pick a few. You can change these any time. | "Tell us your vibe ✨" |
| Moving date | **When did you move (or when will you)?** We'll work out the state deadlines from that date. | Bare `mm/dd/yyyy` input |
| Health, all good | **All 12 Chicago sources updated in the last 6 hours.** | "12/12 sources ok" with a glowing dot in the header |

---

## 2. Fonts

### 2.1 Decision
| Role | Family | License | Why |
|---|---|---|---|
| **Display** (h1–h3, featured titles, wordmark, editorial ledes) | **Newsreader** (Production Type, `google/fonts/ofl/newsreader`) | SIL OFL 1.1 | A news serif drawn for screens: calm, authoritative, warm without being quirky. It gives the editorial voice of The Infatuation and Time Out. The `opsz` axis (6–72) lets us pin one cut tuned for 24–60px. |
| **Text/UI** (everything else, including numbers) | **Inter** 4.x (`google/fonts/ofl/inter`) | SIL OFL 1.1 | The most legible open UI sans, with excellent tabular figures (`tnum`) for dates, times and prices. It's what Linear uses. Neutral enough to let the serif carry the brand. |
| **Mono** | none shipped. Health page IDs use `ui-monospace, "SF Mono", Menlo, Consolas, monospace`. | n/a | Mono appears only on the Health page. It's not worth 20KB+. |

Considered and rejected:
- **Fraunces:** too characterful (the WONK/SOFT axes read as a trendy 2021 startup).
- **Source Serif 4:** fine, but more academic and less warm at display sizes.
- **Literata:** a book face, a little heavy for headlines.
- **Geist:** OFL 1.1, verified. Good, but its techy, Vercel-associated look pushes the site toward "dev tool".
- **Public Sans:** government-neutral and too cold.
- **IBM Plex:** corporate.

### 2.2 What to ship (measured, latin subset, woff2)
| File | Built from | Axes kept | Size |
|---|---|---|---|
| `inter-latin-var.woff2` | `Inter[opsz,wght].ttf` | `wght` 400–700, `opsz` pinned at 14 | **37.5 KB** |
| `newsreader-latin-var.woff2` | `Newsreader[opsz,wght].ttf` | `wght` 400–600, `opsz` pinned at 36 | **37.7 KB** |
| *(optional, v2)* `newsreader-italic-latin-500.woff2` | `Newsreader-Italic[opsz,wght].ttf` | static 500, opsz 36 | 24.3 KB, lazy, not preloaded |

For reference (measured): full Inter opsz+wght = 83.9 KB, Inter static 400 = 22.9 KB, Inter static 600 = 23.6 KB, full Newsreader = 126.5 KB, Newsreader wght 400–600 with the full opsz range = 88.5 KB.

**Budget:** total ≤ 80 KB of fonts on first load (we're at 75.2 KB). Both files are preloaded. There is no italic in v1: `font-synthesis: none`, and emphasis uses weight. Weights used: Inter 400 / 500 / 600 (700 only for the wordmark-sized numerals in the date block if needed); Newsreader 400 / 500 / 600.

Build commands (one-off script, `scripts/build_fonts.sh`, with outputs committed to `web/public/fonts/` plus the `OFL.txt` files):
```bash
fonttools varLib.instancer "Inter[opsz,wght].ttf" opsz=14 wght=400:700 -o inter-inst.ttf
fonttools varLib.instancer "Newsreader[opsz,wght].ttf" opsz=36 wght=400:600 -o newsreader-inst.ttf
UNI="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2190-2199,U+2212,U+2215,U+FEFF,U+FFFD"
FEAT="kern,liga,calt,tnum,case,ccmp,locl,mark,mkmk,frac,sups"
for f in inter-inst newsreader-inst; do
  pyftsubset $f.ttf --unicodes="$UNI" --layout-features="$FEAT" --flavor=woff2 --desubroutinize --output-file=$f.woff2
done
```
(fontTools gotcha: if you instance and subset in one Python process, save and reload the instanced font before subsetting, or `gvar` throws `KeyError`.)

### 2.3 `@font-face` with CLS-free fallbacks (overrides computed against the real fallback files)
```css
@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-latin-var.woff2") format("woff2");
  font-weight: 400 700; font-style: normal; font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2190-2199, U+2212, U+2215, U+FEFF, U+FFFD;
}
@font-face {
  font-family: "Newsreader";
  src: url("/fonts/newsreader-latin-var.woff2") format("woff2");
  font-weight: 400 600; font-style: normal; font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2190-2199, U+2212, U+2215, U+FEFF, U+FFFD;
}
/* Metric-matched fallbacks: text reflows by ~0px when the web font swaps in. */
@font-face { font-family: "Inter Fallback"; src: local("Arial"), local("ArialMT");
  size-adjust: 107.31%; ascent-override: 90.28%; descent-override: 22.48%; line-gap-override: 0%; }
@font-face { font-family: "Newsreader Fallback"; src: local("Georgia");
  size-adjust: 97.01%; ascent-override: 75.76%; descent-override: 27.32%; line-gap-override: 0%; }
/* Georgia missing (Android/Linux): Times New Roman values */
@font-face { font-family: "Newsreader Fallback TNR"; src: local("Times New Roman"), local("TimesNewRomanPSMT");
  size-adjust: 106.50%; ascent-override: 69.02%; descent-override: 24.88%; line-gap-override: 0%; }
```
```html
<link rel="preload" href="/fonts/inter-latin-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/newsreader-latin-var.woff2" as="font" type="font/woff2" crossorigin>
```
Stacks (in tokens): `--font-sans: "Inter", "Inter Fallback", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;` and `--font-serif: "Newsreader", "Newsreader Fallback", "Newsreader Fallback TNR", ui-serif, Georgia, serif;`.

Measured metrics, for re-derivation:
- Inter at opsz 14 / wght 400: avg width 0.4715 em, ascent 0.9688, descent 0.2412, x-height 0.546, cap height 0.728.
- Newsreader at opsz 36 / wght 500: avg width 0.4239 em, ascent 0.735, descent 0.265, x-height 0.426, cap height 0.670.

Newsreader's x-height is small, so **don't set it below 20px**, and set display sizes about 8% larger than you would for a sans.

Type features: body `font-feature-settings: "kern","calt"`. Any number column (dates, times, prices, counts) uses `font-variant-numeric: tabular-nums`. All-caps micro labels use `font-feature-settings: "case"` with `letter-spacing: 0.06em`.

---

## 3. Design tokens

There are three layers, and components may only read layer 3 (or layer 2 when no component token exists):
1. **Primitive:** raw ramps (`--sand-500`).
2. **Semantic:** meaning (`--color-text-muted`). Dark mode is a remap at this layer only.
3. **Component:** per-component knobs (`--card-pad`).

### 3.1 Color model
- **Neutrals: "Sand"**, a warm gray with very low chroma (warm hue around 80°, so not blue chrome). It gives a paper-like feel without the beige of the current `#fbf7f2`.
- **One accent: "Ember"** (`#B8421F` light / `#E8775A` dark), a deep terracotta. It keeps continuity with today's orange but is darker, so white text passes AA (5.47:1), and it's less "app".
  - Used for: the primary button, links, the focus ring, the selected nav item underline and the today marker. **Never for backgrounds of large areas, never for category, never for status.**
- **Semantic status colors** are text-first and tints-second, used only for real state: positive (Free, open), caution (closing in 3–14 days, stale), critical (≤48h, full, cancelled, source down), info (notices).
- **Category hues** (§6) appear only in generated art and in the 8px category swatch. They're never used for text, never for card borders, never for pins.

### 3.2 Verified contrast (WCAG 2.x; ≥4.5 needed for text, ≥3.0 for UI boundaries, focus rings and large text)
Light theme:
| Pair | Ratio |
|---|---|
| text `#1F1D1A` on canvas `#FCFBF8` / surface `#FFFFFF` | 16.25 / 16.81 |
| text-secondary `#5F5A52` on canvas / sunken `#F3F1EC` / sand-100 `#ECE9E2` | 6.61 / 6.06 / 5.64 |
| text-muted `#6F6A61` on canvas / surface / sunken | 5.19 / 5.37 / 4.76 |
| text-muted on sand-100 (hover bg) | **4.43, fails.** Rule: on hover and selected backgrounds use text-secondary, never muted. |
| input border `#8F897F` on surface | 3.47 |
| hairline `#E2DED5` | decorative only. Never the sole boundary of an input or button (WCAG 1.4.11). |
| accent button: white on `#B8421F` / hover white on `#963518` | 5.47 / 7.45 |
| link `#A63C1C` on canvas / surface | 6.18 / 6.39 |
| accent text `#963518` on accent-soft `#FDF3EF` / `#FBE3D9` | 6.83 / 6.06 |
| focus ring `#B8421F` on canvas | 5.29 |
| positive `#1E6B3D` on surface / tint `#EDF7F0` | 6.51 / 5.94 |
| caution `#85540A` on surface / tint `#FDF6E3` | 6.42 / 5.95 |
| critical `#B42328` on surface / tint `#FDEEEE`; white on critical | 6.54 / 5.80 / 6.54 |
| info `#2B579F` on surface / tint `#EEF3FC` | 7.08 / 6.36 |
| inverse: white on `#1F1D1A` | 16.81 |

Dark theme:
| Pair | Ratio |
|---|---|
| text `#F3F1EC` on canvas `#151412` / surface `#1F1D1A` / raised `#2A2824` | 16.31 / 14.90 / 13.03 |
| text-secondary `#C9C4BA` on surface | 9.68 |
| text-muted `#A39D93` on canvas / surface / raised | 6.84 / 6.25 / 5.47 |
| input border `#6F6A61` on surface / canvas | 3.13 / 3.43 |
| accent button: `#1A0D08` text on `#E8775A` | 6.53 |
| link `#F0947A` on canvas / surface; on accent-soft `#3A1A10` | 8.08 / 7.38 / 6.91 |
| focus `#E8775A` on canvas | 6.33 |
| positive `#6FCB93` / caution `#E8B85A` / critical `#F28B8B` / info `#8DB0EE` on surface | 8.52 / 9.16 / 7.08 / 7.67 |
| the same on their dark tints (`#15291D` / `#2E2410` / `#3A1D1D` / `#18233A`) | 7.78 / 8.31 / 6.44 / 7.15 |

Add a vitest that recomputes these pairs from the token file, so a token edit can't silently break AA (idea #9).

### 3.3 Type scale (fluid between a 360px and a 1280px viewport)
| Token | Min → max | Family / weight / line-height / tracking | Use |
|---|---|---|---|
| `--fs-xs` | 12px | Inter 500 / 1.4 / +0.01em | captions, source line, map attribution |
| `--fs-sm` | 14px | Inter 400–500 / 1.45 | meta lines, chips, table cells |
| `--fs-base` | 16px | Inter 400 / 1.55 | body (up from 15px) |
| `--fs-md` | 17 → 18px | Inter 600 / 1.35 / -0.005em | list-row titles, button-large |
| `--fs-lg` | 19 → 22px | Newsreader 500 / 1.25 / -0.005em | h3, featured card title |
| `--fs-xl` | 22 → 28px | Newsreader 500 / 1.2 / -0.01em | h2, section heads, day headers |
| `--fs-2xl` | 26 → 36px | Newsreader 500 / 1.15 / -0.015em | h1 on inner pages, event title |
| `--fs-3xl` | 32 → 46px | Newsreader 500 / 1.1 / -0.02em | city landing h1 |
| `--fs-display` | 38 → 60px | Newsreader 400 / 1.05 / -0.025em | home hero only |
Micro-label (all caps): 11px Inter 600, `letter-spacing: .06em`, with the `case` feature. Use it only for the date-block month and table headers. **No other uppercase text.** Today, category labels and panel headings are uppercase, and this removes them.

### 3.4 Spacing, grid, breakpoints
- **4px base, 8px rhythm:** `--space-1..12` = 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96.
- **Breakpoints:** `sm 480`, `md 768`, `lg 1024`, `xl 1280` (min-width, mobile-first). CSS custom properties can't be used in media queries, so they're documented here and used literally.
- **Container:** max 1200px content. Page margin is 16px below 768, 24px for 768–1023, 32px from 1024 up. Reading measure for prose is max 68ch.
- **Columns:** 4 columns with a 16px gutter below 768; 8 columns with 20px at 768–1023; 12 columns with 24px from 1024 up.
- Vertical rhythm: section gap 48px mobile / 64px desktop. Heading-to-content gap 16px. List rows have 16px top and bottom padding.

### 3.5 Radii, borders, elevation
- **Radii:** `--radius-xs 4` (chips inside inputs, swatches), `--radius-sm 6` (inputs, buttons, chips), `--radius-md 10` (cards, popovers, date block), `--radius-lg 14` (sheets, art tiles, map), `--radius-full 999` (avatars and pins only).
- **Pill shapes are retired** for buttons, tabs, search and selects. 6px corners read as "tool"; 999px everywhere reads as "toy".
- **Borders:** 1px everywhere. The hairline (`--color-border`) separates content. The strong border (`--color-border-strong`) bounds inputs. Selected states use a 2px inner ring via `box-shadow: inset 0 0 0 2px`.
- **Elevation:** surfaces are flat by default.
  - `--shadow-1` is used only for the sticky header after scroll.
  - `--shadow-2` is for popovers and menus.
  - `--shadow-3` is for sheets and dialogs.
  - In dark mode, elevation is expressed by a lighter surface (`surface → raised → overlay`) plus a 1px border, and shadows are near-invisible.

### 3.6 Motion
- **Durations:** `--dur-instant 80ms` (press), `--dur-fast 120ms` (hover color, checkbox), `--dur-base 180ms` (popover, chip toggle), `--dur-slow 260ms` (sheet, drawer).
- **Easing:** `--ease-standard: cubic-bezier(.2,0,0,1)` (enter), `--ease-exit: cubic-bezier(.3,0,1,1)`.
- **Allowed motion:** color, opacity, and translate ≤ 8px for things entering (popover, toast). Sheets slide from their edge.
- **Not allowed:** hover lifts (`translateY(-2px)`), scale-on-hover, spinners, parallax, staggered list reveals, animated counters, skeleton shimmer faster than 1.6s.
- **`prefers-reduced-motion: reduce`:** durations drop to 0.01ms, except that opacity fades are kept at 120ms (fades don't trigger vestibular issues). Map `flyTo` becomes `setView`.

### 3.7 z-index
`--z-base 0`, `--z-raised 1` (whole-card link overlay targets), `--z-sticky 100` (day headers), `--z-header 200`, `--z-popover 300`, `--z-sheet 400`, `--z-dialog 500`, `--z-toast 600`, `--z-skip 700`. Leaflet panes sit inside a `isolation: isolate` wrapper so its internal 400/1000 values can't escape.

### 3.8 Ready-to-paste token block
```css
/* ===== Layer 1: primitives ===== */
:root {
  /* Sand: warm neutral */
  --sand-0:#FFFFFF; --sand-25:#FCFBF8; --sand-50:#F7F5F0; --sand-75:#F3F1EC; --sand-100:#ECE9E2;
  --sand-200:#E2DED5; --sand-300:#C9C4BA; --sand-400:#A39D93; --sand-500:#8F897F; --sand-600:#6F6A61;
  --sand-700:#5F5A52; --sand-800:#3A3732; --sand-850:#2A2824; --sand-900:#1F1D1A; --sand-950:#151412;
  /* Ember: the one accent */
  --ember-50:#FDF3EF; --ember-100:#FBE3D9; --ember-200:#F6C3AF; --ember-300:#F0947A; --ember-400:#E8775A;
  --ember-500:#D4532D; --ember-600:#B8421F; --ember-650:#A63C1C; --ember-700:#963518; --ember-800:#722914;
  --ember-900:#3A1A10; --ember-950:#1A0D08;
  /* Status */
  --green-50:#EDF7F0; --green-700:#1E6B3D; --green-300:#6FCB93; --green-950:#15291D;
  --amber-50:#FDF6E3; --amber-700:#85540A; --amber-300:#E8B85A; --amber-950:#2E2410;
  --red-50:#FDEEEE;   --red-700:#B42328;   --red-300:#F28B8B;   --red-950:#3A1D1D;
  --blue-50:#EEF3FC;  --blue-700:#2B579F;  --blue-300:#8DB0EE;  --blue-950:#18233A;

  /* type */
  --font-sans: "Inter", "Inter Fallback", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-serif: "Newsreader", "Newsreader Fallback", "Newsreader Fallback TNR", ui-serif, Georgia, serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --fs-xs: 0.75rem; --fs-sm: 0.875rem; --fs-base: 1rem;
  --fs-md: clamp(1.0625rem, 1.038rem + 0.1087vw, 1.125rem);
  --fs-lg: clamp(1.1875rem, 1.114rem + 0.3261vw, 1.375rem);
  --fs-xl: clamp(1.375rem, 1.228rem + 0.6522vw, 1.75rem);
  --fs-2xl: clamp(1.625rem, 1.38rem + 1.087vw, 2.25rem);
  --fs-3xl: clamp(2rem, 1.658rem + 1.522vw, 2.875rem);
  --fs-display: clamp(2.375rem, 1.837rem + 2.391vw, 3.75rem);
  --lh-tight: 1.1; --lh-snug: 1.25; --lh-normal: 1.45; --lh-relaxed: 1.55;
  --fw-regular: 400; --fw-medium: 500; --fw-semibold: 600; --fw-bold: 700;

  /* space (4/8) */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:20px; --space-6:24px;
  --space-7:32px; --space-8:40px; --space-9:48px; --space-10:64px; --space-11:80px; --space-12:96px;

  /* shape */
  --radius-xs:4px; --radius-sm:6px; --radius-md:10px; --radius-lg:14px; --radius-full:999px;
  --border-width:1px;

  /* motion */
  --dur-instant:80ms; --dur-fast:120ms; --dur-base:180ms; --dur-slow:260ms;
  --ease-standard:cubic-bezier(.2,0,0,1); --ease-exit:cubic-bezier(.3,0,1,1);

  /* z */
  --z-base:0; --z-raised:1; --z-sticky:100; --z-header:200; --z-popover:300; --z-sheet:400;
  --z-dialog:500; --z-toast:600; --z-skip:700;

  /* layout */
  --container-max:1200px; --measure:68ch;
  --page-margin:16px;
}
@media (min-width: 768px)  { :root { --page-margin:24px; } }
@media (min-width: 1024px) { :root { --page-margin:32px; } }

/* ===== Layer 2: semantic (light) ===== */
:root, :root[data-theme="light"] {
  color-scheme: light;
  --color-canvas: var(--sand-25);
  --color-surface: var(--sand-0);
  --color-sunken: var(--sand-75);
  --color-raised: var(--sand-0);
  --color-overlay: var(--sand-0);
  --color-hover: var(--sand-100);          /* never put text-muted on this */
  --color-scrim: rgb(21 20 18 / .48);

  --color-text: var(--sand-900);
  --color-text-secondary: var(--sand-700);
  --color-text-muted: var(--sand-600);
  --color-text-inverse: var(--sand-0);
  --color-text-disabled: var(--sand-400);   /* only with a non-color cue */

  --color-border: var(--sand-200);          /* decorative hairline */
  --color-border-strong: var(--sand-500);   /* input/button boundary, 3.47:1 */
  --color-divider: var(--sand-100);

  --color-accent: var(--ember-600);
  --color-accent-hover: var(--ember-700);
  --color-accent-text: var(--ember-650);    /* links */
  --color-accent-soft: var(--ember-50);
  --color-accent-soft-strong: var(--ember-100);
  --color-on-accent: var(--sand-0);
  --color-focus: var(--ember-600);

  --color-positive: var(--green-700);  --color-positive-soft: var(--green-50);
  --color-caution:  var(--amber-700);  --color-caution-soft:  var(--amber-50);
  --color-critical: var(--red-700);    --color-critical-soft: var(--red-50);
  --color-info:     var(--blue-700);   --color-info-soft:     var(--blue-50);

  --shadow-1: 0 1px 0 var(--sand-200);
  --shadow-2: 0 1px 2px rgb(31 29 26 / .06), 0 6px 16px rgb(31 29 26 / .08);
  --shadow-3: 0 2px 6px rgb(31 29 26 / .08), 0 20px 48px rgb(31 29 26 / .16);

  /* art (category hue comes from --art-h on the element) */
  --art-bg-l:.95;  --art-bg-c:.030;
  --art-mid-l:.84; --art-mid-c:.070;
  --art-ink-l:.48; --art-ink-c:.100;
  --art-acc-l:.70; --art-acc-c:.120;
}

/* ===== Layer 2: semantic (dark) =====
   One block, no duplication: an inline <head> script resolves the theme BEFORE first paint, so CSS
   only needs [data-theme="dark"]:
   <script>(function(){var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark")
     t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";
     document.documentElement.dataset.theme=t;})()</script>
   (Also listen to matchMedia change events while no explicit choice is stored.) */
:root[data-theme="dark"] {
  color-scheme: dark;
  --color-canvas: var(--sand-950);
  --color-surface: var(--sand-900);
  --color-sunken: #100F0E;
  --color-raised: var(--sand-850);
  --color-overlay: var(--sand-850);
  --color-hover: var(--sand-850);
  --color-scrim: rgb(0 0 0 / .6);

  --color-text: var(--sand-75);
  --color-text-secondary: var(--sand-300);
  --color-text-muted: var(--sand-400);
  --color-text-inverse: var(--sand-950);
  --color-text-disabled: var(--sand-600);

  --color-border: var(--sand-800);
  --color-border-strong: var(--sand-600);   /* 3.13:1 on surface */
  --color-divider: var(--sand-850);

  --color-accent: var(--ember-400);
  --color-accent-hover: var(--ember-300);
  --color-accent-text: var(--ember-300);
  --color-accent-soft: var(--ember-900);
  --color-accent-soft-strong: #4A2215;
  --color-on-accent: var(--ember-950);
  --color-focus: var(--ember-400);

  --color-positive: var(--green-300);  --color-positive-soft: var(--green-950);
  --color-caution:  var(--amber-300);  --color-caution-soft:  var(--amber-950);
  --color-critical: var(--red-300);    --color-critical-soft: var(--red-950);
  --color-info:     var(--blue-300);   --color-info-soft:     var(--blue-950);

  --shadow-1: 0 1px 0 var(--sand-800);
  --shadow-2: 0 0 0 1px var(--sand-800), 0 8px 24px rgb(0 0 0 / .4);
  --shadow-3: 0 0 0 1px var(--sand-800), 0 24px 56px rgb(0 0 0 / .55);

  --art-bg-l:.27;  --art-bg-c:.030;
  --art-mid-l:.36; --art-mid-c:.050;
  --art-ink-l:.80; --art-ink-c:.080;
  --art-acc-l:.62; --art-acc-c:.100;
}

/* ===== Layer 3: component ===== */
:root {
  --header-h: 64px;
  --header-bg: color-mix(in srgb, var(--color-canvas) 92%, transparent);

  --btn-h: 40px; --btn-h-sm: 32px; --btn-h-lg: 48px;
  --btn-px: 16px; --btn-radius: var(--radius-sm); --btn-font: 600 var(--fs-sm)/1 var(--font-sans);
  --btn-primary-bg: var(--color-accent); --btn-primary-bg-hover: var(--color-accent-hover); --btn-primary-fg: var(--color-on-accent);
  --btn-secondary-bg: var(--color-surface); --btn-secondary-border: var(--color-border-strong); --btn-secondary-fg: var(--color-text);
  --btn-quiet-fg: var(--color-text); --btn-quiet-bg-hover: var(--color-hover);

  --input-h: 44px; --input-radius: var(--radius-sm); --input-border: var(--color-border-strong);
  --input-bg: var(--color-surface); --input-px: 12px;

  --chip-h: 32px; --chip-px: 12px; --chip-radius: var(--radius-sm);
  --chip-bg: var(--color-surface); --chip-border: var(--color-border-strong);
  --chip-bg-on: var(--color-text); --chip-fg-on: var(--color-text-inverse);

  --card-pad: var(--space-4); --card-radius: var(--radius-md); --card-gap: var(--space-4);
  --row-pad-y: var(--space-4);
  --datebox-w: 56px; --datebox-h: 60px;

  --focus-ring: 0 0 0 2px var(--color-canvas), 0 0 0 4px var(--color-focus);

  --pin-size: 12px; --pin-size-active: 20px; --pin-fill: var(--color-text); --pin-stroke: var(--color-surface);
  --pin-fill-active: var(--color-accent);
}

/* base hooks */
html { font-family: var(--font-sans); font-size: 100%; background: var(--color-canvas); color: var(--color-text); }
body { font-size: var(--fs-base); line-height: var(--lh-relaxed); font-synthesis: none; -webkit-font-smoothing: antialiased; }
h1, h2, h3 { font-family: var(--font-serif); font-weight: var(--fw-medium); text-wrap: balance; }
:focus-visible { outline: none; box-shadow: var(--focus-ring); border-radius: var(--radius-sm); }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; scroll-behavior: auto !important; }
  .fade { transition: opacity 120ms linear !important; }
}
```

---

## 4. Component specs

The conventions in this section: px values are at a 16px root; "hit" is the minimum tap target (44×44 on touch and pointer-coarse devices, with a minimum of 32px tall on desktop if the hit area is padded to 44 with `::after`).

### 4.1 Header / nav
- **Anatomy (≥1024):** a 64px bar.
  - Left: wordmark.
  - Center-left: the city switcher, 16px after the wordmark.
  - Primary nav (text links): **Events · Deadlines · Calendar · Map · New in town**.
  - Right: search icon button (on ≤1023 only), **Saved** (bookmark icon plus label), theme toggle (in an overflow menu, not a top-level button).
- **Nav item:** 14px Inter 500, `--color-text-secondary`, 0 12px padding, full 64px height hit. **Selected:** `--color-text` with a 2px `--color-accent` bar at the bottom edge (inset 0 12px) and `aria-current="page"`. Hover: `--color-text`. **No filled pills, no count bubbles.** Deadlines may show a plain-text count in muted digits ("Deadlines 3"), and only when items close within 7 days.
- **Health** leaves the nav. A footer link plus an inline stale notice is enough (see §4.12).
- **Sticky:** `position: sticky; top: 0`, background `--header-bg` with `backdrop-filter: blur(12px)`. Add `--shadow-1` only after `scrollY > 0` (IntersectionObserver sentinel).
- **Mobile (<768):** a 56px bar with the wordmark (19px), the city switcher (compact: city name plus chevron) and a menu button. Primary nav moves to a **bottom tab bar**: 5 items, 56px plus the safe-area inset, icon 20px plus 11px label, selected = text plus accent icon. This replaces the horizontally clipped tab row.
- **Accessibility:** `<header>` > `<nav aria-label="Primary">`. The skip link is the first focusable element. The bottom bar is a second `<nav aria-label="Sections">` (same links; don't duplicate in the top bar on mobile).

### 4.2 City switcher
- **Trigger:** "Chicago" in 15px Inter 600 plus a 16px chevron. No pin icon, no pill border. It's a quiet button with a hover background, 6px radius, 36px tall.
- **Panel:** a popover (≥768), 360px wide, `--shadow-2`, 10px radius, 8px padding. A full-screen sheet on mobile. The top has a search input ("Search cities"). Below it, list rows (44px): the city name at 15px/500, the state in muted text on the right, and a check mark on the current city. Optional muted second line: "1,593 events · updated 2 h ago".
- **Behavior:** combobox pattern (`role="combobox"`, `aria-expanded`, a listbox with `aria-activedescendant`). Up/down/Enter/Esc work. Typing filters. Selection navigates to `#/{slug}/feed` and keeps the filters that make sense across cities (when, cats, free), dropping near/tags.

### 4.3 Search
- **Field:** 44px tall, 6px radius, 1px `--color-border-strong`, 16px search icon inset 12px, placeholder "Search events, venues, neighborhoods". The text must be ≥16px so iOS doesn't zoom.
- **Focus:** the focus ring plus `border-color: transparent`. A clear (×) button appears when there's a value.
- **Results:** live-filter the feed (debounce 150ms). Announce "{n} events" in an `aria-live="polite"` region, throttled to 1 announcement per second.
- **Shortcut:** `/` focuses search (desktop), shown as a muted `kbd` hint inside the field at ≥1024.

### 4.4 Filter bar
Primary filters must fit **one line on desktop and one line plus a "Filters" button on mobile.** Today it takes 4 rows and about 200px.
- **Desktop (≥1024), one 48px row:** `[Search (flex 1, max 420)] [When ▾] [Category ▾] [Price ▾] [More filters ▾]`, with the results count right-aligned in muted 14px ("1,593 events"). Each control is a 40px "filter button": 6px radius, 1px strong border, 14px/500 label.
  - **When:** a menu with Today / Tomorrow / This weekend / Next 7 days / Next 30 days / Pick dates…
  - **Category:** a menu of checkboxes grouped by family, each with its 8px swatch.
  - **Price:** Free only / Under $20 / Under $50 / Any.
  - **More filters:** a 480px popover containing Good for meeting people, Size, Neighborhood/near and Tags (checkbox list).
  - **Active state:** the control label changes to the value ("This weekend", "Music + 2", "Free") and the border becomes 1px `--color-text`. No fill color.
- **Applied filters row** (appears only when ≥1 filter is set): removable chips (32px, 6px radius, label plus × with `aria-label="Remove Free only"`), then "Clear all" as a quiet link.
- **Quick picks** (category landing and home only, not the feed): one horizontally scrollable row of up to 8 chips. It's the only chip row on any page.
- **Mobile (<768):** a sticky row under the header with `[Search field]` and `[Filters (2)]`. The "When" segmented control sits beneath: 4 options, Today · Weekend · 7 days · 30 days, 36px tall, `--color-sunken` track, selected = `--color-surface` with a 1px strong border. No overflow clipping, and the labels are shortened to fit 360px.
- **Mobile sheet:** a bottom sheet at 92dvh with a 12px top radius, a drag handle (36×4, sand-300) and the title "Filters".
  - Sections are separated by 1px dividers, with 24px between sections: When (radio list), Category (checkbox list with family swatches, collapsible children), Price, Good for meeting people (switch), Size, Neighborhood (select), Tags.
  - A sticky footer holds `[Clear all]` (quiet) and `[Show 214 events]` (primary, full width, with a live count).
  - Focus is trapped while open. Esc and a scrim tap close it. Focus returns to the trigger.

### 4.5 Event card
There are three variants, sharing one data-to-signal function (§4.6).

**a) List row (the default in the feed, deadlines, saved and search).**
- **Layout (≥768):** `grid-template-columns: 56px 1fr auto; column-gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--color-divider);`.
  - No box, no shadow and no left color bar. The divider separates rows. The day header separates groups.
  - Col 1 is the date block (§4.7). Inside a day group where the date is already in the header, col 1 shows **the time** instead ("7:30 PM" in 14px/600 tnum, stacked as "7:30" over "PM").
  - Col 2:
    - Line 1: the category label in 13px/500 `--color-text-secondary`, prefixed by an 8×8 swatch (radius 2, `oklch(var(--art-ink-l) var(--art-ink-c) var(--art-h))`), "·", then the neighborhood.
    - Line 2: the title in 17–18px Inter 600 `--color-text`, max 2 lines (`-webkit-line-clamp: 2`), as a link with a whole-row hit area via `::after`.
    - Line 3: the meta line in 14px `--color-text-secondary`: `Venue name · $12–$20` (price as plain text; "Free" in `--color-positive`, weight 500).
    - Line 4 (optional): the status line (§4.6) in 14px/500 with a 14px icon.
  - Col 3 is the actions column: a Save icon button (36×36 visual, 44 hit, bookmark outline → filled `--color-text`, `aria-pressed`). The outbound CTA lives on the detail page, not the row. The row is for scanning; one consistent action means less noise.
- **Mobile:** the same grid at `48px 1fr auto`, title 17px.
- **States:** hover = background `--color-hover` with 8px of horizontal bleed (`margin-inline: -8px; padding-inline: 8px; border-radius: 10px`). There is no lift. Focus-visible on the title link = the focus ring on the whole row (use `:has(a:focus-visible)`). Visited: none. Past events are not shown; if one appears in Saved, the row text becomes muted and the status line reads "Took place Oct 12".
- **Recurring:** append "· Repeats weekly" to the meta line, or "+3 more dates" as a muted link that opens the detail page. Not a badge.

**b) Compact row (calendar agenda, map list, "similar", plan steps).**
- 44px min height: `[time 64px, tnum, muted] [title 15px/500, 1 line, ellipsis] [price 14px muted, right]`. No art and no status. A critical status is reduced to a 6px `--color-critical` dot before the time, with a `title` and an sr-only text equivalent.

**c) Featured card (home, city landing "Picks this week", category landing hero row). At most 3–6 per page.**
- A vertical card, no border, radius 14 on the art only.
  - Art tile 16:10 (§6) with `border-radius: 14px; overflow: hidden`, then 12px space.
  - Eyebrow: the date line in 13px/600 `--color-accent-text` ("Sat, Oct 17 · 7 PM"). This is the only place the accent colors text besides links.
  - Title: Newsreader 500, `--fs-lg`, 2 lines max.
  - Meta: the neighborhood · price in 14px secondary.
  - Optional "why" line: 14px muted, 1 line ("A no-experience-needed league with a free-agent list").
- **Grid:** 3 columns at ≥1024, 2 at ≥640, a horizontal scroll-snap row on mobile (cards 78vw, 16px gap, `scroll-snap-type: x mandatory`; the next card peeks to signal scroll).
- **Hover:** the title gets an underline (1px, offset 3px). The art doesn't zoom.

**Accessibility for all variants:**
- Each card is an `<article aria-labelledby={titleId}>`, and the title is the only link.
- Save is a separate `<button>`.
- The art is `aria-hidden="true"`, `role="presentation"`.
- Date and time use `<time datetime="2026-10-17T19:30:00-05:00">`.
- The status line includes text, never color alone.

### 4.6 Price, availability, deadline and other signals: quiet, max 3 per card
Each card shows **one meta line (price is part of it), at most one status line, and at most one tag**. That's 3 signals max. The status line shows the first matching rule; everything else is on the detail page.

| Priority | Condition (data that must exist) | Status line text | Tone |
|---|---|---|---|
| 1 | `stale` | "Listing may be out of date · checked 3 days ago" | caution |
| 2 | cancelled / postponed | "Cancelled" / "Postponed to Nov 2" | critical |
| 3 | full (`spots_left == 0`) | "Full" / "Full · waitlist open" | muted text plus icon |
| 4 | registration `closes_at` published, ≤ 48h | "Registration closes tomorrow, 11:59 PM" / "…closes today at 6 PM" | critical |
| 5 | `closes_at` published, 3–14 days | "Registration closes Thu, Oct 22" | caution |
| 6 | `spots_left ≤ max(5, 25% of total)` | "4 of 24 spots left" | caution |
| 7 | `selling_fast` (real ticket signal only) | "Selling quickly" | caution |
| 8 | registration required, no date (`method: derived`) | "Registration required" | secondary text, no color |
| 9 | `closes_at` > 14 days | "Registration open until Nov 30" | secondary |
| none | otherwise | no status line | – |

- **Price (always in the meta line when known):** "Free" | "$12" | "$12–$20" | "From $39 · 3 sellers" (count only if >1 seller). Unknown price shows nothing (never "$?" or "Price TBA").
- **Tag slot (≤1):** chosen in this order: "Good for meeting people" (social ≥ 0.75) › "Good to go solo" › "Beginner friendly" › "New this week" (first listed ≤ 3 days ago). It's rendered as 13px secondary text after a `·` at the end of the status line, or alone on line 4. It's never a colored pill.
- **Detail-page only:** weather, attendance estimate, price trend, source list, "why recommended", "Registration open" (redundant with "Registration required").
- **Icons in status lines:** clock (deadline), users (spots), alert-triangle (stale/cancelled), 14px, `currentColor`.

### 4.7 Date block
- 56×60, radius 10, background `--color-surface`, border 1px `--color-border`, centered stack:
  - month: 11px Inter 600, uppercase, `.06em`, `case`, `--color-text-muted` ("OCT");
  - day: 24px Inter 600, tnum, `--color-text`, line-height 1 ("17");
  - weekday: 12px/500 `--color-text-secondary` ("Sat").
- **Today:** the month slot reads "TODAY" in `--color-accent-text`, and the border is 1px `--color-accent`.
- **Multi-day:** day shows "17–19", or for a month crossover "Oct 30" over "– Nov 2" at 13px. All-day events show no time.
- **Accessibility:** wrap in `<time>` and give the block an `aria-label="Saturday, October 17"` because the abbreviations read badly.
- **Date-format rules (all in the city's timezone):**
  - Day header: "Today · Fri, Oct 16", "Tomorrow · Sat, Oct 17", then "Sun, Oct 18". After 6 days, include the year only if it differs ("Sat, Jan 9, 2027").
  - Times: "7 PM" and "7:30 PM". Ranges are "7–10 PM" or "11 AM–2 PM", with an en dash and no spaces. Midnight is "12 AM". Noon is "Noon".
  - Date-only listings (midnight start, no end) show no time ("All day" only if the source says all-day).
  - If the viewer's timezone differs from the city's, append the abbreviation once per page in the day header ("Times in CT").
  - Relative times ("in 3 hours", "checked 2 h ago") only for <24h. Otherwise absolute.

### 4.8 Event detail page
This is a real page at the existing route `#/city/event/id`, not a side drawer. The drawer is kept only on the map view, where context matters.
- **≥1024:** a 12-column grid. Main is 7 columns, a 1-column gap, and the aside is 4 columns, sticky at `top: calc(var(--header-h) + 24px)`.
- **Breadcrumb** (13px muted): "Chicago › Music › Live music".
- **Header:**
  - The art tile (§6) full-width in main, 21:9 ratio, radius 14. If a static map snippet is a better image (venue known, art category "other"), use the map instead (§6.5).
  - Category label with swatch.
  - **Title** in Newsreader 500 `--fs-2xl`, max 3 lines.
  - Venue · neighborhood in 16px secondary.
- **Aside "ticket card":** `--color-surface`, 1px border, radius 14, padding 24.
  - When: "Sat, Oct 17", with "7:30–10 PM" below in 15px/600 tnum, plus "Add to calendar" (quiet link, downloads .ics).
  - Where: the venue as a link to the map, then the address in secondary text.
  - Price: "$12–$20 · via Ticketmaster, SeatGeek".
  - Status line (§4.6).
  - **Primary CTA**, full width at 48px, named for the destination: "Get tickets on Ticketmaster ↗". Secondary: Save (secondary button, full width), then Share (quiet).
  - Under the CTA, in 12px muted: "We don't sell tickets. You'll finish on ticketmaster.com."
- **Main sections**, with `--fs-xl` Newsreader headings and 40px between sections:
  1. **About**: the source description with a max of 68ch, "Read more" after 8 lines.
  2. **Good to know**: a definition list (2 columns ≥768) with Weather, Expected crowd ("About 150–300 people · estimated from venue capacity"), Accessibility, Age, Good for meeting people ("why" reasons as a sentence).
  3. **Registration** (if any): the deadline in text, the evidence quote in a quote block (left 2px `--color-border-strong`, 16px Newsreader 400, cite in 12px muted with a link), and the spots.
  4. **Prices**: the offers table (seller, type, from, link), plus a sparkline only if `window_hours ≥ 24` (1.5px `--color-text` line, no fill).
  5. **Location**: a static map (§6.5) at 16:9, radius 14, with "Open in Maps" / "Directions" quiet links.
  6. **Where this comes from**: a source list with last-checked times, "Report a problem" (mailto or GitHub issue link), and the methodology link.
  7. **Similar this week**: up to 5 compact rows.
- **<1024:** a single column. The ticket card moves directly under the header (not sticky). A **sticky bottom CTA bar** (64px plus the safe area, surface plus top border) holds the price on the left and the primary CTA on the right. It appears after the in-flow CTA scrolls out of view.
- **Accessibility:**
  - `<main>` gets an `<h1>` (the title).
  - On route entry, move focus to the h1 (`tabindex="-1"`).
  - Outbound links get "(opens in new tab)" as sr-only text.

### 4.9 Map: pins and clusters
- **Basemap:** keep OSM standard raster tiles (policy-compliant light use, with attribution) but **calm them with CSS on the tile pane only**:
  - Light: `.leaflet-tile-pane { filter: grayscale(1) contrast(.92) brightness(1.04); }`.
  - Dark: `filter: grayscale(1) invert(1) contrast(.85) brightness(.9);`.
  - This keeps the attribution intact (it's in the control pane, which isn't filtered).
  - Later (idea #6): self-hosted Protomaps PMTiles city extracts with a "light/grayscale" flavor (OSM data, ODbL, same attribution), with no third-party tile server.
- **Pins:** a 12px circle, fill `--pin-fill` (ink), 2px `--pin-stroke`. **One color for all categories.** 15 hues on a map is noise, and category is a filter, not a legend.
  - Hover/focus: 16px.
  - Selected: 20px `--pin-fill-active` (Ember) with a 3px white stroke and `--shadow-2`.
  - Events in the next 24h get a 2px offset ring in `--color-text` (a "soon" cue without color).
  - Hit area: 32px (transparent `divIcon` padding).
- **Clusters:** a white circle (`--color-surface`), 1px `--color-border-strong`, `--color-text` count in 13px/600 tnum. Size steps: 28px (<10), 36px (10–99), 44px (100+). No colored halos.
- **Layout ≥1024:** a split view with the list (5 columns, compact rows, scrolls) and the map (7 columns, sticky full height minus the header). Hovering a row highlights its pin and vice versa. Moving the map shows "Search this area" (secondary button, top center) instead of auto-refiltering.
- **Mobile:** the map is full height with a bottom sheet list that has 3 snap points (peek 120px, half, full).
- **Accessibility:**
  - The map is supplementary. The list is the accessible equivalent, and the map container gets `aria-label="Map of 323 events. The list below has the same events."`.
  - Pins are focusable buttons, in list order.
  - Keyboard: +/- zoom, arrow keys pan (Leaflet default).

### 4.10 Calendar: month and agenda
- **Month grid (≥768):** 7 columns, cell min height 96px, 1px `--color-divider` grid lines (a table look, not floating tiles).
  - Day number: 13px/600 tnum, top-left, 8px inset.
  - Up to 2 event titles per cell (12px, 1 line, ellipsis, muted), then "+5 more" (12px link).
  - Today: the day number in a 24px circle with 1px `--color-accent` border and `--color-accent-text`.
  - Selected: cell background `--color-accent-soft` and day number `--color-text`.
  - Past days: muted text, still focusable.
  - Weekend columns: `--color-sunken` background in light mode only (very subtle).
- **Mini month (mobile and the aside):** 40×40 cells. Under the number, show a density marker of 0–3 4px dots in `--color-text-muted` (1 = 1–4 events, 2 = 5–14, 3 = 15+). No category colors.
- **Agenda:** day headers (`--fs-lg` Newsreader, sticky at `top: var(--header-h)`, canvas background, bottom hairline), then compact rows. Empty days are skipped, and a muted line notes the gap ("Nothing listed Oct 21–23").
- **Accessibility:**
  - The month is a `role="grid"` with arrow-key navigation (←→ day, ↑↓ week, Home/End for week bounds, PgUp/PgDn for month).
  - Each cell gets `aria-label="Saturday, October 17, 12 events"`.
  - Selection updates the agenda, and the agenda heading receives focus on Enter.

### 4.11 Deadlines list
- The page header is h1 "Deadlines" plus a lede.
- Groups are h2 Newsreader `--fs-xl`: **This week**, **Next two weeks**, **Later this season**, **Ongoing sign-ups** (no date).
- **Row:** `grid-template-columns: 72px 1fr auto`, 16px vertical padding, divider.
  - Col 1, deadline "date block" variant: the month and day of the **deadline**, with "CLOSES" as the micro-label above in muted text.
  - Col 2:
    - Line 1: the event/league title, 17px/600.
    - Line 2: what the deadline is, in secondary text ("Fall coed kickball · season starts Nov 1 · $65 per player").
    - Line 3: the status text per §4.6 (critical only if ≤48h).
  - Col 3: secondary button "Register ↗" (≥768). On mobile it moves under col 2.
- **New-resident to-dos (state requirements)** become a separate section at the top, framed as a checklist: a card with surface background, 1px border, radius 14, padding 24.
  - The h2 is "Moving to Texas: official deadlines".
  - Under it sits the move-date field (a labeled date input, 44px, with helper text "We use this to work out your due dates. It stays on this device.").
  - Rows have a checkbox (local only), title (link to the official page), "Due Sun, Nov 15 · 30 days after your move" and "Source: txdmv.gov · checked 3 h ago" in 12px muted.
  - **No colored background**, and links aren't styled orange-underlined as titles. The title is text, with "Official page ↗" as a quiet link.
- **Empty:** see §1.3 copy, with no icon or a 24px muted calendar icon at most.

### 4.12 Plan / onboarding ("New in town")
- **Steps:** 1 Moving date → 2 Interests → 3 Neighborhood (optional) → 4 Your plan.
  - Progress is shown as "Step 2 of 4" text (13px muted) plus a 2px track (sand-200) with an ink fill. No segmented candy bar.
  - The container is max 640px wide, centered, with no card chrome (the page is the card).
  - h1 is Newsreader `--fs-2xl`, with a one-sentence helper below in 16px secondary.
  - Navigation: "Back" (quiet) on the left, "Continue" (primary) on the right, sticky on mobile. "Skip" is a link under the content for optional steps.
- **Interest picker:** checkbox tiles in a grid (2 columns mobile, 3 desktop), 64px tall, 1px strong border, radius 10. Each tile has an 8px swatch, the label at 15px/600, and a muted example ("Kickball, softball, bowling").
  - Selected: a 2px inset `--color-text` ring plus a check icon top-right.
  - Native `<input type="checkbox">` sits inside a `<label>`.
- **The plan:** a timeline list grouped by "This week", "Before Nov 1", "This month". Each item is a compact row with a reason line ("Your league interest · registration closes Oct 22"). No scores, no percentages, no "level up".

### 4.13 Health / status page
Modeled on public status pages (Stripe and Atlassian Statuspage style), which are a trust asset.
- **Summary banner:** text only, an icon plus a sentence in 18px/500. "All 12 Chicago sources updated in the last 6 hours." Or the caution version: "2 of 12 sources are behind. Their last good listings are still shown, marked as possibly out of date." Then "Last full rebuild: Fri, Oct 16, 9:14 AM CT".
- **Source table:** columns Source, Covers ("Park District programs"), Status (icon plus word: Operational / Delayed / Down / Disabled by robots.txt), Last success, Events, and 30-day history.
  - The history is 30 bars, each 4×20, 2px gap. Bar colors: positive = ok, caution = degraded, critical = failed, sand-200 = no run. Each bar has an `aria-label` and the table has a text summary ("29 of 30 days OK").
  - A mobile layout stacks each source as a row with the history beneath.
- **Data quality section:** counts of reported / derived / estimated / curated fields with methodology links.
- **IDs** use `--font-mono` 13px.
- **The header freshness pill is removed.** Instead, when any source is stale, a one-line notice appears above the feed (`--color-caution-soft` background, radius 10, 12px 16px padding): "Some Park District listings may be out of date. [Details]". The footer always has "Data status" with a 6px status dot.

### 4.14 Footer
- Background is `--color-sunken`, with a top hairline, 48px padding top and 64px bottom.
- 4 columns at ≥1024 (2 on mobile):
  - **Get Off the Couch** (wordmark at 19px plus a one-line description);
  - **Cities** (the 11 links);
  - **About** (How it works / Methodology, Data sources, Data status, Privacy);
  - **Elsewhere** (Report a problem, Suggest a source, GitHub, if public).
- The bottom row is in 12px muted: "Event details belong to their organizers; we link to the original listing. Map data © OpenStreetMap contributors. Updated Fri, Oct 16, 9:14 AM CT."

### 4.15 Empty, error and skeleton states
- **Empty:** left-aligned (not centered hero), max 480px.
  - An h2 at `--fs-lg` Newsreader stating the fact.
  - One sentence of explanation or next step in 16px secondary.
  - At most 1 primary or secondary action.
  - No illustration, emoji or big colored icon. Optional: a 32px muted line icon.
- **Error:** the same structure. The icon is an alert-circle in `--color-critical`. The copy says what failed, what we did ("showing what we had at 9:14 AM") and the action ("Try again"). Use a `role="alert"` region only for errors caused by a user action. Load errors render inline.
- **Skeleton:**
  - It replaces the spinner. List-row skeletons match the exact row geometry (56×60 date block, then 3 bars: 120×12, 70%×18, 50%×14) in `--color-sunken`. Render 6 rows.
  - Shimmer: opacity 1 → .6 → 1 over 1.6s ease-in-out. Off with reduced motion.
  - Show the skeleton only after 150ms (avoid a flash) and for at least 300ms once shown.
  - `aria-busy="true"` on the region, plus an sr-only "Loading events".

### 4.16 Buttons, links and inputs
- **Buttons:** heights 32 / 40 / 48. Padding 12 / 16 / 20. Radius 6. 14px (16px for lg) Inter 600. Icon 16px with an 8px gap. Trailing ↗ for outbound links.
  - **Primary:** accent background, `--color-on-accent`. Hover: `--color-accent-hover`. Active: the same plus `filter: brightness(.95)`. Disabled: `--color-sunken` background, `--color-text-disabled` text, `cursor: not-allowed`, plus `aria-disabled` (keep it focusable when the reason is explained via `aria-describedby`).
  - **Secondary:** surface background, 1px strong border, text color. Hover: `--color-hover`.
  - **Quiet:** transparent with text color. Hover: `--color-hover`.
  - **Destructive** (only on "Clear saved"): critical text with a critical 1px border.
  - **One primary button per view region.**
  - No shadows. No transforms. Press feedback is background only.
- **Links:** `--color-accent-text`, underline 1px with 3px offset. In body copy, the underline is always on. In UI lists, it's off at rest and on at hover. Visited is unchanged.
- **Inputs:** 44px, radius 6, 1px strong border, 12px padding, 16px text. The label sits above in 14px/500 `--color-text` with an 8px gap. Helper text below in 13px muted. Error: 1px critical border, an icon plus text below in critical, `aria-invalid`, `aria-describedby`.
- **Select:** a native `<select>` with a custom chevron (keep it native for mobile).
- **Checkbox / radio:** 20px with a 44px label hit area. Checked = ink fill with a white check (the accent is reserved).
- **Switch:** only for "Good for meeting people" in the sheet. 36×20, ink when on.
- **Focus** is the same everywhere: a 2px canvas gap plus a 2px focus ring (`--focus-ring`).

---

## 5. Page templates

All templates use `--container-max` 1200, `--page-margin`, the header from §4.1 and the footer from §4.14.

| Page | Route | Structure (desktop ≥1024, top to bottom) | Mobile differences |
|---|---|---|---|
| **Home** | `#/` | 1) Hero, 8 columns left-aligned: kicker "Your city, made easy." 14px/600 muted; h1 `--fs-display` "Everything worth leaving the house for, and every deadline you'd otherwise miss."; lede 18px secondary; city search input (44px, 420px wide) "Which city are you in?". 2) **Cities**: a 3-column grid of city tiles. Each tile has a 16:9 neighborhood color-field art (§6, seeded by city slug), city name in Newsreader `--fs-lg`, "1,593 events · 14 deadlines", no health dot. 3) **How it works**: 3 columns, each a Newsreader `--fs-lg` heading plus 2 sentences ("From official sources", "Checked every few hours", "Deadlines, not just dates"). 4) Footer. | The hero is 1 column with no image. City tiles are a 1-column list (row: name, counts, chevron). |
| **City landing** | `#/chicago` (new) or the feed's "All" state | 1) h1 `--fs-3xl` "Chicago" with the lede "What's on this week, and what's due." plus a "Last updated 9:14 AM" muted line. 2) **Picks this week**: 3 featured cards. 3) **Deadlines this week**: up to 4 deadline rows plus "All deadlines →". 4) **This weekend**: the date line "Fri, Oct 16 – Sun, Oct 18" plus 8 list rows plus "See all 214 →". 5) **Browse by category**: a 4-column grid of category tiles (art tile 4:3 plus label plus count). 6) **New in town?** A callout (sunken background, radius 14, 32px padding): heading, sentence, secondary button "Make a plan". | Featured cards become a horizontal snap row. The category grid is 2 columns. |
| **Category landing** | `#/chicago/feed?cats=sports_league` (renders as a landing when exactly one family is selected and nothing else) | Breadcrumb; h1 "Rec & beer leagues in Chicago"; a 2-sentence lede from the taxonomy; a quick-pick chip row of child categories; "Open registrations" (deadline rows for the family); then the standard feed (filter bar plus day-grouped list rows). | Same, stacked. |
| **Events (feed)** | `#/chicago/feed` | Filter bar (§4.4); stale notice if any; an optional "Picks this week" collapsed to 3 featured cards **only when no filters are set**; day groups with sticky day headers and list rows. Right rail (4 columns, ≥1280 only): "Closing soon" (3 deadline compact rows) and a mini month calendar. Pagination: "Show 50 more" secondary button, centered, plus a count "Showing 50 of 1,593". | No rail. Bottom tab bar. |
| **Event** | `#/chicago/event/{id}` | §4.8 | §4.8 |
| **Deadlines** | `#/chicago/deadlines` | h1 "Deadlines"; lede "League sign-ups, registration cutoffs and early-bird prices in Chicago, soonest first."; the state to-dos card (§4.11); grouped deadline rows; a methodology footnote ("How we find deadlines →"). 8-column content width (max 800). | Same, full width. |
| **Calendar** | `#/chicago/calendar` | h1 plus month nav ("‹ October 2026 ›", plus a "Today" quiet button); the month grid at 8 columns; the agenda for the selected day at 4 columns (sticky). | Mini month on top (sticky collapsed to a week strip on scroll), agenda below. |
| **Map** | `#/chicago/map` | The filter bar in compact form (search plus When plus Filters), then the list/map split (§4.9). | The map with a bottom sheet list. |
| **New in town / plan** | `#/chicago/plan` | §4.12 wizard; once complete, the plan page: h1 "Your first month in Chicago", the move date with "Change", and timeline sections. | Same. |
| **Saved** | `#/chicago/saved` | h1 "Saved"; a muted note "Saved on this device. Share a link to move them."; actions "Share list" and "Download calendar (.ics)"; list rows grouped Upcoming / Past. | Same. |
| **Data status (health)** | `#/chicago/health` | §4.13. | The table becomes stacked rows. |
| **About / methodology / privacy** | `#/about` (+ anchors) | Prose template: max 68ch, h1 `--fs-2xl`, h2 `--fs-xl`, body 17px/1.6. A left sticky table of contents (3 columns) at ≥1024. Sections: What this is · Where the data comes from (sources table) · How we estimate (crowd size, deadlines) · What we don't do (sell tickets, track you) · Privacy (local storage only; no analytics cookies; what the server logs) · Contact. | The table of contents becomes a `<details>` "On this page". |

---

## 6. Imagery system (we can't use event photos)

### 6.1 Options evaluated
| Option | Looks established? | Distinguishes events? | Legal/ops risk | Effort | Verdict |
|---|---|---|---|---|---|
| A. Pure typographic cards (no image) | Yes (Resy, Time Out lists) | Weak; walls of text on landing pages | None | 1 | **Use for list and compact rows** |
| B. Category illustration set (hand-drawn, ~15 pieces) | Yes if commissioned well | Only by category; repeats look cheap fast | Need an illustrator/license | 4 | Reject for v1 |
| C. **Generated geometric pattern art, seeded by event id, motif per category family, palette per family (OKLCH)** | Yes; reads like a designed editorial system (Spotify/Apple Music editorial covers, The Browser Company) | Yes: unique per event, consistent per category | None (our own SVG) | 2–3 | **Chosen for featured cards, event header, category and city tiles** |
| D. Static map snippets per event | Honest and useful | Yes (place) | **OSM tile policy forbids bulk prefetch/scraping of tiles**; client-side for 1 map per page is fine, per-card is heavy use | 2 | Use **only** on the event page (Location section, and as the header when the category is "other") |
| E. Monograms (venue initials) | OK, but looks like an avatar fallback | Weak | None | 1 | Use only as a fallback inside C for "other" |
| F. Neighborhood color fields | Pretty, but neighborhoods aren't always known | Medium | None | 1 | Folded into C: city tiles on the home page are seeded by city slug |

### 6.2 Decision
**Typography-first everywhere, plus a deterministic SVG "poster" generator for the ≤ 6 hero surfaces per page.** List rows never get art. The art is abstract (no fake photos, no text inside), and is decorative and `aria-hidden`. Variation comes from `hash(event.id)`, which is a sticky canonical id, so art never changes between builds. Category gives the palette and motif, so a page of leagues looks related and a mixed page looks curated.

### 6.3 Palette per family (OKLCH hue; lightness/chroma are global tokens per theme, so all families have equal visual weight)
`--art-h` values: music 295 · nightlife 330 · volunteer 10 · food_drink 45 · community 75 · arts 95 · family 115 · outdoors 135 · sports_league 155 · fitness 175 · learning 200 · trivia_games 225 · sports_watch 250 · niche 275 · other 70 with chroma ×0 (stone).

Each piece uses 4 tones built as `oklch(var(--art-X-l) var(--art-X-c) var(--art-h))`, where X ∈ {bg, mid, ink, acc}. Light and dark are handled by the tokens, so the SVG itself is theme-agnostic. Generated SVGs reference `var(--art-bg)` etc. The wrapper defines:
```css
.art { --art-bg: oklch(var(--art-bg-l) var(--art-bg-c) var(--art-h));
       --art-mid: oklch(var(--art-mid-l) var(--art-mid-c) var(--art-h));
       --art-ink: oklch(var(--art-ink-l) var(--art-ink-c) var(--art-h));
       --art-acc: oklch(var(--art-acc-l) var(--art-acc-c) calc(var(--art-h) + var(--art-shift, 0)));
       background: var(--art-bg); border-radius: var(--radius-lg); overflow: hidden; aspect-ratio: var(--art-ratio, 16/10); }
.art[data-family="other"] { --art-bg-c: 0; --art-mid-c: 0; --art-ink-c: 0; --art-acc-c: .02; }
.art svg { display: block; width: 100%; height: 100%; }
```
`--art-shift` is seeded to −20, 0 or +20 degrees, for slight variety inside a family.

### 6.4 Motifs (one per family; every motif is ≤ 60 SVG elements, viewBox 0 0 160 100)
| Family | Motif | Seeded parameters |
|---|---|---|
| music | **Grooves**: 6–10 concentric arcs from a corner, alternating stroke widths 2/6 | corner (4), ring count, stroke ratio, one ring in `acc` |
| nightlife | **Halftone**: a dot grid whose radius falls off from a seeded focal point | focal x/y, grid pitch 8–12, max r 3–5 |
| volunteer | **Linked rings**: 3–5 overlapping circles in a row or arc | count, radius, baseline y, which ring is filled |
| food_drink | **Table**: 1 big circle (plate), 2–4 small circles, 1 rounded bar (utensil-like, abstract) | positions, sizes |
| community | **Quilt**: a 4×6 grid of squares, each with one of {blank, half-diagonal, quarter-circle} | per-cell shape and rotation |
| arts | **Arches**: 3–5 nested semicircles (rainbow-arch) on a ground line | count, center x, thickness |
| family | **Pebbles**: 5–8 rounded rects (rx = h/2) scattered without overlap | sizes, positions (rejection sampling, max 40 tries) |
| outdoors | **Contours**: 6–9 stacked smooth sine paths (topographic) | amplitude, frequency, phase, vertical spacing |
| sports_league | **Field**: stripes (mowed-grass bands) plus a center circle and halfway line in `ink` at 1.5px | stripe count 5–8, orientation, circle r |
| fitness | **Pace**: 8–14 parallel diagonal bars of varying length | angle 20–40°, lengths |
| learning | **Ruled**: horizontal rules every 10px plus one vertical margin rule in `acc` plus 0–2 underline marks | rule offset, margin x |
| trivia_games | **Tiles**: a 5×8 grid of rounded squares, 3–5 "flipped" to `acc` | flipped indices |
| sports_watch | **Pennants**: 3–6 chevrons/triangles in a row | count, direction, size |
| niche | **Constellation**: 6–10 four-point stars connected by 1px lines | positions, sizes |
| other | **Monogram field**: a large venue-initial glyph is NOT used (it would read as text); instead 3 overlapping rectangles in stone | positions |
| city tiles (home) | **Grid of blocks**: an abstract street grid of 6–10 rectangles with 2 "park" blocks in `acc` | seeded by city slug |

### 6.5 Static map rule
On the event page only, render a non-interactive Leaflet map (zoom 15, dragging off, `keyboard: false`) with the same grayscale tile filter and a single Ember pin. One map per page view is light use, within the OSM tile policy. Never pre-render map images at build time from `tile.openstreetmap.org` (bulk download is prohibited). Keep the attribution visible. If self-hosted PMTiles land later (idea #6), this can become a build-time static image.

### 6.6 Generator spec (TypeScript, drop into `web/src/lib/art.ts`)
```ts
// Deterministic, theme-agnostic SVG art. Same id → same picture, forever.
export type Family = "music"|"nightlife"|"volunteer"|"food_drink"|"community"|"arts"|"family"|"outdoors"
  |"sports_league"|"fitness"|"learning"|"trivia_games"|"sports_watch"|"niche"|"other";

export const ART_HUE: Record<Family, number> = { music:295, nightlife:330, volunteer:10, food_drink:45, community:75,
  arts:95, family:115, outdoors:135, sports_league:155, fitness:175, learning:200, trivia_games:225,
  sports_watch:250, niche:275, other:70 };

/** FNV-1a 32-bit */
export function hash(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return h >>> 0;
}
/** mulberry32: tiny, fast, good enough for art */
export function rng(seed: number): () => number {
  let a = seed;
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
type R = () => number;
const pick = <T,>(r: R, xs: readonly T[]): T => xs[Math.floor(r() * xs.length)];
const between = (r: R, lo: number, hi: number) => lo + r() * (hi - lo);
const f = (n: number) => Math.round(n * 10) / 10; // 1 decimal keeps strings short

const W = 160, H = 100;
const T = { bg: "var(--art-bg)", mid: "var(--art-mid)", ink: "var(--art-ink)", acc: "var(--art-acc)" } as const;

type Motif = (r: R) => string;
const MOTIFS: Record<Family, Motif> = {
  music: (r) => {
    const [cx, cy] = pick(r, [[0, 0], [W, 0], [0, H], [W, H]] as const);
    const n = 6 + Math.floor(r() * 5), step = 150 / n, accent = Math.floor(r() * n);
    let s = "";
    for (let i = 1; i <= n; i++)
      s += `<circle cx="${cx}" cy="${cy}" r="${f(i * step)}" fill="none" stroke="${i === accent ? T.acc : i % 2 ? T.ink : T.mid}" stroke-width="${i % 2 ? 2 : 6}"/>`;
    return s;
  },
  nightlife: (r) => {
    const fx = between(r, 20, W - 20), fy = between(r, 15, H - 15), p = 16 + Math.floor(r() * 5), max = between(r, 4, 7);
    let s = "";
    for (let x = p / 2; x < W; x += p) for (let y = p / 2; y < H; y += p) {
      const d = Math.hypot(x - fx, y - fy) / 110, rad = max * (1 - d);
      if (rad > 0.6) s += `<circle cx="${f(x)}" cy="${f(y)}" r="${f(rad)}" fill="${d < 0.15 ? T.acc : T.ink}"/>`;
    }
    return s; // pitch ≥16 on 160×100 → at most 10×6 = 60 dots; asserted in tests
  },
  outdoors: (r) => {
    const n = 6 + Math.floor(r() * 4), amp = between(r, 4, 10), freq = between(r, 1, 2.2), ph = r() * Math.PI * 2;
    let s = "";
    for (let i = 0; i < n; i++) {
      const y0 = (H / (n + 1)) * (i + 1); let d = `M0 ${f(y0)}`;
      for (let x = 8; x <= W; x += 8) d += ` L${x} ${f(y0 + amp * Math.sin((x / W) * freq * Math.PI * 2 + ph + i * 0.35))}`;
      s += `<path d="${d}" fill="none" stroke="${i === 2 ? T.acc : T.ink}" stroke-width="1.5" stroke-linejoin="round"/>`;
    }
    return s;
  },
  // …the remaining motifs follow §6.4 with the same helpers. Each returns ≤60 elements using only T.* fills.
} as Record<Family, Motif>;

export interface ArtOptions { id: string; family: Family; title?: string }
const cache = new Map<string, string>();

/** Returns an SVG string. Wrap it in <div class="art" data-family=… style="--art-h:…;--art-shift:…" aria-hidden="true">. */
export function artSvg({ id, family }: ArtOptions): { svg: string; hue: number; shift: number } {
  const key = `${family}:${id}`;
  const seed = hash(key), r = rng(seed);
  const shift = pick(r, [-20, 0, 20] as const);
  let svg = cache.get(key);
  if (!svg) {
    const rot = pick(r, [0, 180] as const); // only 0/180 so 16:10 tiles never letterbox
    const body = (MOTIFS[family] ?? MOTIFS.other)(r);
    svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" focusable="false">`
      + `<rect width="${W}" height="${H}" fill="${T.bg}"/><g transform="rotate(${rot} ${W / 2} ${H / 2})">${body}</g></svg>`;
    cache.set(key, svg);
  }
  return { svg, hue: ART_HUE[family] ?? 70, shift };
}
```
Preact usage:
```tsx
export function Art({ id, family, ratio = "16/10" }: { id: string; family: Family; ratio?: string }) {
  const { svg, hue, shift } = artSvg({ id, family });
  return <div class="art" data-family={family} aria-hidden="true"
    style={{ "--art-h": hue, "--art-shift": shift, "--art-ratio": ratio }} dangerouslySetInnerHTML={{ __html: svg }} />;
}
```
- **Safety:** the SVG contains only numbers and constant strings. No event text ever enters it, so `dangerouslySetInnerHTML` is XSS-safe by construction. Add a test that `artSvg` output matches `/^[<>\w\s="\-.:/#(),;%]+$/` and contains no data fields.
- **Tests (vitest):**
  1. Same input gives the identical string.
  2. 1,000 random ids produce ≥ 950 distinct SVGs per family.
  3. Element count ≤ 60.
  4. Byte length ≤ 3 KB.
  5. Snapshot one id per family.
- **Performance:** at most about 6 art tiles per page. The 3 KB cap keeps it to about 18 KB of inline SVG, and generation is under 1ms each.
- **Open Graph:** later, render the same SVG plus the title to a 1200×630 PNG at build time with `@resvg/resvg-js` for share previews (idea #8).

---

## 7. Critique of the current design (from `docs/screenshots/after/*` and `app.css`)

What makes it read as an "app demo" rather than an established site, and the concrete fix for each:

1. **Badge soup.**
   - Problem: a single Chicago card shows **"Registration required" + "$163" + "Registration open" + "Meet people" + "☀ 64°F"**, then 3 lines of purple sparkle text ("Pickleball: great for meeting people · Easy to show up solo · Registration closes in 5 days"), then "via Chicago Park District adult … · 3h ago", Save, and Register. That's about 10 signals per card. "Registration required" and "Registration open" are redundant. The deadline appears twice (pill and why-line).
   - Fix: §4.6, with max 3 signals in a fixed priority. Weather, the why-line, attendance and source move to the detail page.
2. **The same fact encoded three times in color.** Category hue is the 4px left bar (`.card::before`), the tinted date block (`hsl(var(--h) …)`) and the colored uppercase category label. Fifteen hues times three encodings makes a rainbow grid.
   - Fix: neutral date block, neutral category text with one 8px swatch. Hue appears only in art (§6).
3. **Seven semantic tints in play at once.** `good`, `warn`, `hot`, `info`, `social` (purple), `accent-soft` and the category tints. Purple "social" is an extra brand color.
   - Fix: one accent plus four status colors used only for real state. Delete `--social*`.
4. **Pills everywhere (`border-radius: 999px`).** Tabs, chips, buttons, search, selects, city button, freshness indicator, segmented control and badges are all pills. That's the hallmark of a component-library demo.
   - Fix: 6px radius for controls. Full radius only for pins and avatars.
5. **Logo as an app icon.**
   - Problem: an accent squircle rotated −6° with a colored glow shadow (`.logo { transform: rotate(-6deg); box-shadow: 0 6px 16px -6px var(--accent) }`), plus the "ur city made easy" subtitle under the name.
   - Fix: a serif wordmark, no tile, no tagline in the header (§1).
6. **Control overload above the fold.**
   - Problem: on desktop Chicago, the first event card starts at y≈377px. Above it are 4 rows of controls: search plus a 5-option segmented control, 9 category chips (the last one clipped, "Trivia" faded), 13 tag chips (clipped), and a row of 2 toggles plus 3 selects. On mobile the nav tabs clip mid-word ("M…") and the time selector clips ("Next 30 …").
   - Fix: a one-row filter bar with menus, a mobile sheet and a bottom tab bar (§4.4, §4.1).
7. **A notification-style count bubble.** A red `.tabs .count` circle on "Deadlines 1" reads like an unread badge, which is a gamification and attention cue.
   - Fix: plain muted digits, shown only for ≤7-day deadlines.
8. **Dev-ops chrome in the header.** "Updated 6m ago · 12/12 sources ok" with a glowing green dot. It's trustworthy information in the wrong place: it looks like a monitoring dashboard.
   - Fix: footer "Data status" plus an inline notice when something is actually stale (§4.13).
9. **Hover lifts and glow.** `.card:hover { transform: translateY(-2px) }`, `.btn:hover { transform: translateY(-1px) }`, `.city-card:hover` lifts, and accent-colored button shadows.
   - Fix: no transforms, background-only hover (§3.6).
10. **Boxed 3-column card grid for a 1,593-item feed.** Equal-height boxes of uneven content leave ragged white gaps (see the Chicago grid: card 1's footer sits about 30px lower than card 2's), and scanning across columns breaks chronology.
    - Fix: dividered list rows grouped by day, like Resy and Time Out (§4.5a). Boxes only for featured.
11. **The "Worth getting off the couch for this week" band** is a peach-gradient container (`.highlights { background: linear-gradient(180deg, var(--accent-soft), transparent) }`) bleeding −12px outside the grid. It reads like a promo slot.
    - Fix: a "Picks this week" section with a Newsreader h2 and 3 featured art cards on a plain canvas.
12. **Typography has no voice.** Everything is system-ui. The display font is `ui-rounded` (SF Pro Rounded on Apple, a fallback elsewhere, so it's inconsistent across platforms and reads "iOS widget"). Body is 15px. Card titles are 1.04rem bold. There are lots of 0.7–0.8rem bold uppercase labels.
    - Fix: Newsreader/Inter, 16px body, a single uppercase micro-label use (§2, §3.3).
13. **The map is visually loud.** Full-color OSM standard tiles plus 15-hue pins with dark outlines. Pins in a cluster like the Seattle core overlap into a blob, and the clusters use the accent with a halo.
    - Fix: a grayscale tile filter, one-color pins, white count clusters, and a list/map split (§4.9).
14. **The Deadlines page leads with a blue-tinted box.** It holds orange underlined link titles and a raw `mm/dd/yyyy` input with an inline label. It's followed by a big centered orange check mark for the empty state, which is celebratory where it should be informative.
    - Fix: §4.11 (a neutral checklist card, a labeled date field, informative empty copy, no check-mark celebration).
15. **Microcopy.** "1593 things" (no thousands separator, flippant), "ur city made easy", "stale" as a badge word, "+3 more dates" as a pill, "☀ 56°F" with a glyph-emoji, and "Register ↗" on every card regardless of where it goes.
    - Fix: the §1.3 table.
16. **The demo banner** uses yellow construction-tape stripes (`repeating-linear-gradient(45deg, #ffd23f …)`).
    - Fix: a calm caution notice bar (`--color-caution-soft`, 14px text: "Sample data. These events aren't real. [See live cities]").
17. **The drawer is the event page.** A 560px right drawer with an 18px heading feels like a modal app, and it can't be bookmarked as a "page" in the user's mind even though the URL exists.
    - Fix: a full event page (§4.8). Keep the drawer only on the map.
18. **Focus ring.** It's a 3px accent outline with a radius hack. It works, but it clashes with pills.
    - Fix: the two-ring `--focus-ring`, the same on every control.

Keep (these are good and on-brand): source attribution on every event, "never invent a countdown" logic (`method: derived`), the freshness model, the registration evidence quote, mobile-first CSS, `prefers-reduced-motion` handling, the skip link, OSM attribution, and URL-encoded filter state.

---

## 8. Idea candidates

Format: `title | area | value 1-5 | effort 1-5 | why`

1. Replace token block + self-host Inter/Newsreader with metric-matched fallbacks | web/foundation | 5 | 2 | Biggest single jump in perceived quality. 75 KB measured, zero CLS, and everything else in this doc builds on it.
2. Card signal budget: one `cardSignals(e)` function enforcing the §4.6 priority (≤3 signals) with unit tests | web/cards | 5 | 2 | Removes badge soup with logic rather than CSS, keeps "never invent urgency" testable, and is reused by list, compact and featured variants.
3. Feed as day-grouped list rows instead of a boxed 3-column grid | web/feed | 5 | 3 | Chronological scanning like Resy and Time Out, no ragged grid gaps, and about 2× the events per screen.
4. One-row filter bar with menus + mobile bottom sheet + applied-filter chips | web/filters | 5 | 3 | Moves the first event from y≈377px to about 180px on desktop and fixes the clipped mobile controls.
5. Deterministic SVG art generator (`art.ts`) for featured cards, event header, category and city tiles | web/imagery | 4 | 3 | Solves "no photos" legally and beautifully. It's stable per event id and theme-aware via OKLCH tokens.
6. Calm map: grayscale tile filter now; self-hosted Protomaps PMTiles per city later; one-color pins and white clusters | web/map | 4 | 2 (filter) / 4 (PMTiles) | The map stops shouting. PMTiles removes the third-party tile dependency and allows static map images at build time.
7. Real event page layout (sticky ticket card, destination-named CTA, "Where this comes from") replacing the drawer | web/event | 5 | 3 | Bookmarkable, shareable and SEO-ready. It puts provenance next to the CTA, which is the core trust message.
8. Build-time Open Graph images (art + title + date) via resvg | web/share | 3 | 2 | Shared links look like an established publication in iMessage and Slack rather than a bare URL.
9. Contrast regression test: vitest recomputes WCAG ratios for every semantic pair in the token file (light + dark) | tests/a11y | 4 | 1 | Locks in the AA numbers in §3.2. Any future token tweak that breaks contrast fails `make check`.
10. Public status page redesign (summary sentence + per-source 30-day history bars), with freshness removed from the header | web/health | 4 | 2 | Turns the pipeline's honesty into a visible trust asset, like Stripe and Atlassian status pages, without dev-ops chrome on every page.
