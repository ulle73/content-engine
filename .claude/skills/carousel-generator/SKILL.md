---
name: carousel-generator
description: >
  Generate a branded Instagram carousel (1080×1350, 4:5) in the "Midnight Bioluminescent"
  glass style. Backgrounds are painted LOCALLY and procedurally (no API, no key, no cost);
  every title, card, chip and frame is code-rendered glass; real web screenshots can be
  captured and framed as proof. Two modes: Claude researches + captures the facts/screenshots,
  or the user supplies their own info/images. Use when the user asks to "make a carousel",
  "make an Instagram carousel", "turn this into a carousel", or "/carousel-generator". Default brand Golfkuponger (@golfkuponger). Windows/content-engine import.
---

# Carousel generator — Midnight Bioluminescent

Makes a scroll-stopping, **data-rich** Instagram carousel that stays perfectly on-brand across
every slide. The world is a void-black meadow lit from inside by a teal bioluminescent bloom;
every UI surface is **glass**; all type is code-rendered (sharp, editable).

Self-contained in `library/kits/carousel-generator/carousel/`. **Runs fully offline — no API key required.**

**content-engine import:** run everything from the repo root with `library/.venv/Scripts/python`.
Generated files go to `work/carousel-generator/` (runs/, output/, photos/, shots/). Relative asset
paths in plan.json resolve against the kit's `carousel/` folder, then `work/carousel-generator/`, then
the repo root. Brand defaults: handle `@golfkuponger`, brand `Golfkuponger`, tagline `golfkuponger.se`
(`carousel_run.py init "<topic>" --handle @x --brand "X"` or per-plan fields). Swedish å/ä/ö render
fine in every template (Google Fonts with latin-ext).

## Golden rules
- **Titles are code, never AI.** The scene is a background, nothing more.
- **Everything is glass.** Cards, screenshot frames, chips, pills, hero captions — one material.
- **ONE glass capsule accent word per slide** (`hero_word`), serif against sans.
- **Type is moon white or fog gray only.** Teal is *light*, never paint. Amber lives only in the
  scene's foreground flora, never in the UI.
- **At least 40% of every slide is unbroken black**, and the top ~45% stays clear for the headline.
- **The middle must carry proof** — a chart, a stat, or a real screenshot. Never empty.
- **Real screenshots get a source caption** (e.g. "via anthropic.com"). Always attribute.
- **Free by default.** `localbg` / `render` / `export` / `build` cost nothing. Only the optional
  kie.ai `generate` step is paid, and it needs explicit user approval first.
- **Facts:** if researching, verify from a primary source. Never invent numbers.

## Three styles ship with the kit (+ pastoral and 90s alternates) — pick one per carousel
| style | plan settings | reference sheet | look |
|---|---|---|---|
| **Midnight Bioluminescent** (default) | `"template":"template.html"`, `"theme":"midnight"` | `assets/styles/midnight.jpg` | void-black meadow lit from inside, everything glass, backgrounds painted locally by `carousel_localbg.py` |
| **Archival Swiss Poster** | `"template":"template-archival.html"`, `"theme":"archival"` | `assets/styles/archival.jpg` | bone paper, brick-red block, oversized clipped headline crossing one hard seam, a real photograph per slide |
| **Celestial Surrealist Collage** | `"template":"template-celestial.html"`, `"theme":"celestial"` | `assets/styles/celestial.jpg` | high-key sky, ionic columns framing every slide, headline set twice, doves + monarch butterflies crossing three depth layers, technical grid on top |

The chart palette follows `theme` automatically (`carousel_charts.use_theme`).

### Archival specifics
- **Brick red is structure**: full-width blocks and bar fills only, *never* type. **All type is bone
  white** (deep ink on paper). Hierarchy is weight and opacity, never colour.
- **One hard seam per slide** — set `seam` (px) per slide, and *vary it across the set*. The colour
  block ends at the seam; the photograph starts there. Only the headline crosses it.
- **The headline is one lowercase word**, auto-fitted to `head_overflow` × the plate width (1.05–1.35)
  so it always clips at both edges; `head_cross` (0.2–0.35) is how much of it falls below the seam.
- **Every slide needs its own photograph.** Never reuse one across slides — the sheet says the
  photograph supplies every other colour. Fetch freely-licensed ones with
  `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/fetch_photos.py work/carousel-generator/photos/<set> "<search>" ...` (Wikimedia
  Commons; public-domain and CC only, credits written to `credits.json`), set each slide's `bg_file`
  to the photo, and put its credit in `meta3` — the slide prints it in the **Archive** field.
- Metadata fields: `meta1` (Location), `meta2` (Date), `meta3` (Archive); footer uses `handle`
  (Designer), `tagline` (Series), `brand_label` (Format).
- Data panels are **deep ink over the photograph** — that is what keeps "all type is bone white" true.

### Celestial specifics
- **All type is cloud white** and always carries a soft shadow. **Monarch orange is butterflies only**;
  **ink black is sticker glyphs and badges only.** Neither may touch a chart — charts run celestial
  blue vs marble cream on a deepened alpine-slate plate.
- **The headline is set twice**: `kicker` (small, tracked) then `headline` (the huge clipped cut,
  auto-fitted to `head_overflow` × the plate width). `subtitle` is the italic serif quote and may
  contain `<br>`.
- **Three depth layers**: `bg_file` is the landscape at the back, the SVG columns are the middle,
  and `flora` (a blossom photo, blurred and masked) is the front. Doves sit behind the flora,
  butterflies and petals in front.
- Per-slide layout: `quote_top`, `head_top`, `content_bottom` (px). Corner words are `meta1` / `meta2`.
- Optional stickers: `glyph` (`"star"` / `"smiley"`) with `glyph_x` / `glyph_y`, and a badge via
  `badge1` / `badge2` / `badge3` + `badge_x` / `badge_y`. All are rotated off-axis automatically.
- **Never use film stills, posters or other copyrighted imagery.** Use freely-licensed photographs of
  the *world* the subject lives in, one per slide, credited.

## Setup (once)
```
library/.venv/Scripts/python -m pip install playwright pillow python-dotenv requests numpy && library/.venv/Scripts/python -m playwright install chromium
```
That's it. (Fonts load from Google Fonts on first render; everything else is local.)

## Two modes (ask the user which)
1. **Claude researches** — Claude web-searches the topic, verifies facts, and captures the relevant
   real charts/screenshots itself.
2. **User provides** — the user gives the copy, numbers, and/or their own screenshots (drop images in
   `work/carousel-generator/shots/`). Claude just lays them out.

## Workflow (all local, all free)
1. **Init** — `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_run.py init "<topic>"` → a run folder + starter plan.
2. **Content** — write/verify the copy and the per-slide `content` blocks (below). Arc = hook →
   body (one idea/slide, ≥1 real screenshot or chart) → CTA. Keep to 5–7 slides.
3. **Scenes** — give each slide a `bg_scene` (see the table below) so neighbouring slides differ.
4. **Screenshots** — capture real charts/posts into `work/carousel-generator/shots/` (see "Screenshots").
5. **Build** — `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_run.py build <run>` = paint backgrounds locally →
   render 1080×1350 PNGs → export to `work/carousel-generator/output/<slug>/`.
6. Open the slides for review; also draft a caption + hashtags.

Individual steps: `localbg` (paint only, `--force` to repaint), `render`, `export`.
Don't like a background? Change that slide's `bg_seed` or `bg_scene` → `localbg <run> --force`.

## Local background painter (`carousel_localbg.py` + `bg_local.html`)
Procedural canvas art: void-black field, a teal plume emitted from *inside* the scene, silhouette
flora (queen anne's lace, dandelion clocks, seed spikes, grass) with rim light that fades along
each stem, starfield, drifting spores, tiny amber florets, vignette, film grain. Seeded — the same
`bg_scene` + `bg_seed` always paints the identical image. ~1s per slide.

| scene | look | use for |
|---|---|---|
| `deep-bloom` | bloom low-centre, deep flora standing in it | the signature slide, hooks |
| `far-field` | wide, quiet, mostly black sky | long headlines |
| `starfield` | near-empty black + stars | one big statement |
| `dandelion` | hero dandelion clock catching the light | one big idea |
| `amber-meadow` | tiny warm amber florets in front | the CTA / warmest slide |
| `mist` | horizontal haze drifting through the light | calm body slides |
| `close-flora` | tall out-of-focus stems in front, light behind | most depth, data slides |

`library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_localbg.py --preview` renders one PNG per scene to compare.
Fine-tune any slide with `bg_tweak` (`bloom{x,y,r,intensity}`, `flora{density,height}`, `horizon`,
`stars`, `spores`, `mist`, `amber`, `topGuard`, `grain`).

## plan.json
**Plan level:** `slug, topic, template, handle` (footer left), `tagline` (footer middle),
`brand_label` (footer right), `canvas`, `slides`.

**Per slide:** `index, role (hook|body|cta), topic_tag` (glass chip, top-left), `kicker`,
`headline` (light serif), `hero_word` (**the** glass capsule; "" hides it), `subtitle` (glass
caption pill), `content` (below), `cta_pill` + `cta_soft` (bright frosted button, e.g. "Join
waitlist" + "now"), `microcopy` (small fog-gray line under it), `bg_scene`, `bg_seed`, `bg_tweak`,
`bg_file`, `out_file`. `image_prompt` is only used by the optional paid path.

### content types (rendered by `carousel_render.build_content`, all in glass)
**Charts** (SVG, from `carousel_charts.py` — vector-crisp at 2x):
- **line** (trend over time): `{"type":"line","title":"…","x_labels":["2010",…],"series":[{"label":"…","values":[…]},{"label":"…","values":[…],"muted":true}],"unit":"","note":["…"]}`
- **column** (magnitude across categories): `{"type":"column","title":"…","unit":"","items":[{"label":"Solar PV","value":0.043,"highlight":true}],"note":["…"]}` — a label may contain `\n` to break onto two lines
- **dumbbell** (before → after): `{"type":"dumbbell","title":"…","from_label":"2010","to_label":"2024","items":[{"label":"Solar PV","from":0.417,"to":0.043}],"note":["…"]}`
- **meter** (one ratio against a limit): `{"type":"meter","title":"…","value":8.75,"max":100,"unit":"%","value_label":"8.7%","cap_label":"of all electricity","left":"…","right":"…"}`

**Chart colour rule — identity is never carried by hue here.** The style sheet allows only teal
(as light), moon white and fog gray, so there is no categorical palette. Use **emphasis** (the series
that matters is lit teal, the rest fog gray — the muted line is also dashed, so identity survives
CVD and grayscale) or the validated single-hue teal ramp for magnitude. Two or more series always get
a legend whose key is a *mark*, never coloured text. Label selectively — the endpoint or the extreme,
never a number on every point. Gridlines are solid hairlines; never a second y-axis.

**Other blocks:**
- **image** (real screenshot — the star): `{"type":"image","src":"assets/shots/x.png","caption":"…","source":"via anthropic.com"}`
- **hero** (big cutout floating on the scene): `{"type":"hero","src":"…","caption":"key stat"}` — pair with `"layout":"hero"`
- **bars**: `{"type":"bars","title":"…","unit":"%","items":[{"label":"…","value":43.3,"highlight":true}],"note":["…","Source: …"]}` — fills glow teal, numbers stay white
- **stats**: `{"type":"stats","title":"…","items":[{"value":"$5","label":"input","delta":"+12% vs 2024","spark":[…12 values…]}],"note":["…"]}` — `spark` adds a sparkline with a lit current point
- **dial**: `{"type":"dial","title":"…","segments":["Low","Medium","High"],"on":[1],"left":"…","right":"…","note":["…"]}`
- **chips**: `{"type":"chips","items":["…","…"]}`

Prefer a **real screenshot** for the "scoop" slides; use bars/stats when no clean screenshot exists.
Dark screenshots sit best in this style — crop light ones tight or redraw them as bars/stats.

## Screenshots (`library/kits/carousel-generator/carousel/scripts/capture.py`)
```
library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/capture.py "<url>" work/carousel-generator/shots/out.png --selector "figure img"
library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/capture.py "<url>" work/carousel-generator/shots/out.png --clip x,y,w,h --scale 2
```
`capture.py` is plain headless Playwright (no user-agent spoofing — removed on import), declines
cookie banners (reject/necessary only) and scrolls to trigger lazy content. Blocked sites: screenshot by hand.
- Find the region by listing large `svg,canvas,img,figure,table` blocks and reading
  `getBoundingClientRect()` + `window.scrollY`; `page.screenshot(clip=…)` clips *within the
  viewport*, so set a tall viewport before clipping below the fold, then clip at scale 2.
- Bot-protected / login-gated sites (e.g. X): use the interactive Claude Browser to find the
  region, then reproduce it with `capture.py`.
- Always set `caption` + `source`.

## Brand / look (`library/kits/carousel-generator/carousel/scripts/template.html`)
Void black `#08080A`, ash `#1A1B1E`, moon white `#FFFFFF`, bioluminescent teal `#3FBFB2`
(light only), ember amber `#E9A33C` (scene flora only), fog gray `#7C7C82`.
Headline + capsule = Cormorant Garamond Light; everything else = Inter.
The glass material is five CSS vars (`--glass-tint/-fill/-edge/-blur/-shadow`) — edit those and
every surface re-skins at once. Full detail in `library/kits/carousel-generator/carousel/knowledge/glass-and-brand.md`.

Alternate templates: `"template":"template-pastoral.html"` (the previous soft-pastoral look) or
`"template-90s.html"` (aged film). The style reference is
`library/kits/carousel-generator/carousel/assets/carousel-style-reference.jpg` — swap that ONE file to change the look.

## Optional PAID backgrounds (kie.ai) — only if the user asks
Put `KIE_API_KEY` in the repo-root `.env`, host the style sheet yourself and set `CAROUSEL_STYLE_REFERENCE_URL` (auto-upload to catbox/0x0 was removed), fill each slide's `image_prompt`, then
`carousel_run.py generate <run>` (Nano Banana Pro, 4:5, bundled reference as style input) →
`render` → `export`. Never spend credits before the user says go. Do NOT use any image MCP.
