---
name: carousel-kit
description: >
  Make finished Instagram carousels (1080×1350, 4:5) for the user's own account. Asks a few
  questions (Instagram handle, niche, topic, do they have their own photos), then either lays their
  OWN photos into editorial layouts, or builds the carousel in one of 6 bundled style sheets
  (Midnight, Archival, Celestial, Chalk-on-Ground, Sun-Faded, Sky-Blue) — free ($0, rendered
  locally) or paid (AI images painted from the style sheet). Text is always code-rendered, facts are
  verified, company logos are real. Default brand: Golfkuponger (@golfkuponger). Use when the user
  says "make a carousel", "Instagram carousel", "karusell", "turn this into a carousel",
  "/carousel-kit", or uploads photos for a post. Windows/content-engine import.
---

# Carousel generator (carousel-kit)

Runtime: `library/kits/carousel-kit/carousel/` (scripts, templates, assets, knowledge).
Everything generated goes to `work/carousel-kit/` (runs/, output/, photos/, shots/, logos/,
my-images/, profile.json). Run all scripts from the repo root with `library/.venv/Scripts/python`.
Relative paths in plan.json resolve against the kit's `carousel/` folder, then `work/carousel-kit/`,
then the repo root. The user should only answer a few questions and approve once. **You do all the work.**

**Brand defaults:** handle `@golfkuponger`, brand `Golfkuponger`, tagline `golfkuponger.se`
(override per plan with `handle`/`brand_label`/`tagline`, or `carousel_run.py init "<topic>"
--handle @x --brand "X"`). For Swedish copy also override the English template defaults
(`cue`, `cta_pill`, `byline`, `lockup`, `credit_text` …) — see `library/kits/carousel-kit/LIBRARY.json` notes.

## 0 · First run in a project (silent, once)
1. `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/doctor.py` — if it says NOT READY, run it with `--fix` and re-check.
   (Needs the venv `library/.venv` built from the signed Python 3.12 — see library/IMPORTING.md.)
2. If `work/carousel-kit/profile.json` exists, you already know this user — greet them by handle, confirm it is
   still right, and skip the questions it answers.

## 1 · Ask these questions (one `AskUserQuestion` round where possible, then wait)
1. **Instagram handle** — e.g. `@brightsmile.dental`. Also ask for a short footer line / tagline (optional).
2. **Niche / business** — what they do and who for (e.g. "roofing, Austin TX, homeowners").
   This decides the voice, the examples, and which styles you suggest.
3. **Topic** — one line, or a pasted script/notes. If they have none, propose 3 topics that fit the niche
   and let them pick.
4. **Do you have your own photos for this?**
   - **Yes → Own-photos mode** (§3). Ask them to either drag the files/folder into this chat (paths
     appear in the message) or drop them into `work/carousel-kit/my-images/inbox/`, then say "done".
   - **No → Style-sheet mode** (§2).
5. **Facts** — "Should I research and fact-check this, or will you give me the facts?"
6. **Slides** — 5, 6 or 7 (default 6).
7. **Logo** — if the topic names a company/product, you will use its real logo; if it's about *their*
   business, ask them for their logo file (optional).

Save the answers to `work/carousel-kit/profile.json` (`handle`, `tagline`, `niche`, `logo`, `default_style`,
`default_mode`) so the next carousel starts faster.

## 2 · Style-sheet mode (no photos of their own)
1. Run `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/gallery.py` — it opens **STYLES.html**, a numbered gallery of every style
   sheet with a real example. Recommend 1–2 styles for their niche (use `best_for` in
   `library/kits/carousel-kit/carousel/styles.json`) and ask them to pick a number.
2. Ask **Free ($0) or Paid?**
   - **Free:** imagery comes from `free_images` in styles.json (local painter, or freely-licensed
     Wikimedia photos via `fetch_photos.py`, always credited). Costs nothing.
   - **Paid:** AI images painted from that style's sheet. Uses the **Higgsfield** connector if it is
     connected in this Claude (GPT Image 2.5, upload the sheet + logo as `image_references`), otherwise
     **kie.ai** (PAID) with `KIE_API_KEY` in the repo-root `.env` plus a PUBLIC style-sheet URL in
     `CAROUSEL_STYLE_REFERENCE_URL` (the automatic catbox/0x0 upload was removed) (`carousel_run.py generate`). Preflight the cost, tell them
     the number of credits, and **never spend anything before they say "go"**. Even on the paid path,
     headlines/numbers are rendered by the template on top — the AI paints the picture only.
3. Continue at §4.

## 3 · Own-photos mode (their photos)
1. Import: `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/import_images.py <set-name> <paths or folder>` (no paths → the
   inbox). It converts iPhone HEIC, fixes rotation, cuts out each subject (free, on-device), and writes
   `work/carousel-kit/my-images/<set-name>/manifest.json` (subject box, empty side, busy areas, accent colours).
2. Read the manifest and pick a layout per photo from `own_layouts` in styles.json using
   `library/kits/carousel-kit/carousel/knowledge/style-own.md` (e.g. subject to one side + calm wall → `editorial`; person centred
   → `orbit`; no person → `editorial`/`punch`). Use `"template":"template-own.html"`, `"theme":"own"`,
   and per slide `bg_file` = the photo, `subject_file` = its cutout, `layout` = the choice.
   Accent colours come from the photo (manifest `accent_candidates`) — never invented.
3. Their photos are private: they stay in `work/carousel-kit/my-images/`, are never uploaded anywhere, and never
   go into a paid generation unless the user explicitly asks.
4. Continue at §4.

## 4 · Plan → approval → build
1. Write the copy with `knowledge/structure.md`, `hooks.md`, `ctas.md` (hook → one idea per slide → CTA),
   in the voice of their niche. Verify every number from a primary source (`data-and-screenshots.md`);
   company/product topics get their real logo (`logos.md`).
2. Show the full plan — every slide's text, visual, photo/layout, and (paid) the credit cost — and **wait
   for approval**.
3. Build: `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/carousel_run.py init "<topic>"` → write `plan.json` (plan-level
   `handle`, `tagline`, `template`, `theme`, `logo`) → free: fetch/paint images, `render`, `export`;
   paid: `generate`, `render`, `export`.
4. Own-photos mode: run `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/check_own.py <run>` (text inside the frame, no overlaps,
   readable contrast on the real pixels) and fix anything it flags. Then, for every mode, **look at every
   exported slide** before showing it (overlaps, clipped text, faces covered, numbers
   hidden, text on busy areas). Fix and re-render until clean.
5. Show the slides from `work/carousel-kit/output/<slug>/`, open the folder, and give a caption + hashtags.

## Rules for every carousel
- **Text is code, never AI.** Headlines, numbers, captions and handles are rendered by the template.
- **5–7 slides, one idea per slide**, and the middle of every slide carries a visual (chart, stat,
  screenshot, photo subject) — never empty.
- **Verify every number** from a primary source; attribute screenshots ("via …") and credit photos.
- **Real logos only** for companies/products (`fetch_logo.py`); on paid generation, upload the logo as
  a reference image AND describe it in the prompt.
- **ONE style sheet per carousel**, and follow that style's own rules (its row + specifics below).
- **Approve before anything paid.** Nothing costs money until the user says "go".

## Adding a new style sheet
If the user gives you their own style-sheet image, follow `library/kits/carousel-kit/carousel/knowledge/new-style-from-a-sheet.md`,
save the sheet to `library/kits/carousel-kit/carousel/assets/styles/<id>.jpg`, and add an entry to `library/kits/carousel-kit/carousel/styles.json` so it
appears in the gallery.

## The style library — pick ONE style per carousel
Every sheet lives in `library/kits/carousel-kit/carousel/assets/styles/`; its rules are in `library/kits/carousel-kit/carousel/knowledge/style-<name>.md`
(where one exists) and its chart colours in `carousel_charts.THEMES` / `scripts/themes/<name>.json`.
| style | plan settings | reference sheet | look |
|---|---|---|---|
| **Midnight Bioluminescent** (default) | `"template":"template.html"`, `"theme":"midnight"` | `assets/styles/midnight.jpg` | void-black meadow lit from inside, everything glass, backgrounds painted locally by `carousel_localbg.py` |
| **Archival Swiss Poster** | `"template":"template-archival.html"`, `"theme":"archival"` | `assets/styles/archival.jpg` | bone paper, brick-red block, oversized clipped headline crossing one hard seam, a real photograph per slide |
| **Celestial Surrealist Collage** | `"template":"template-celestial.html"`, `"theme":"celestial"` | `assets/styles/celestial.jpg` | high-key sky, ionic columns framing every slide, headline set twice, doves + monarch butterflies crossing three depth layers, technical grid on top |
| **Chalk-on-Ground Editorial** | `"template":"template-chalk.html"`, `"theme":"chalk"` | `assets/styles/chalk.jpg` | overhead lawn photo, hand-drawn chalk capitals lying on the grass, one yellow-outline accent word, heavy vignette, "FROM A Creator FOR A Creator" lockup |
| **Sky-Blue Tech Poster** | `"template":"template-skyblue.html"`, `"theme":"skyblue"` | `assets/styles/skyblue.jpg` | navy field + clear-sky photography, white condensed-caps headline with the last line biggest, ONE word re-written in a magenta→orange brush script, the subject cut out and standing in front of the headline |
| **Sun-Faded Photo Poster** | `"template":"template-sunfaded.html"`, `"theme":"sunfaded"` | `assets/styles/sunfaded.jpg` | full-bleed pastoral photograph, one faded-gold serif headline sitting BEHIND the subject (local cutout / sky-key), almost-missed light-sans captions sampled from the photo, no panels |

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
  `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_photos.py work/carousel-kit/photos/<set> "<search>" ...` (Wikimedia
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

### Chalk specifics
- **All lettering is chalk white.** ONE accent word (`hero_word`) may break to highlight yellow, and only as an
  OUTLINE. **Muted red exists only in the footer lockup** ("FOR A"). The greens come from the photo, never the UI.
- **The headline is stacked lines lying on the ground**: set `lines` (or `headline` split on " / "); the block is
  rotated (`tilt`, alternate its sign across the set) and tilted in perspective (`pitch`). Letters are jittered by `seed`.
- **Proof is chalk drawn on the grass**, no panels: stats/bars/charts sit on a soft shadow pool; screenshots are
  prints lying on the ground. A tall proof automatically shrinks the lettering.
- **One top-down lawn photo per slide** — fetch with species names ("Zoysia lawn", "Agrostis lawn"); crop with
  `bg_focus` + `bg_zoom`; credit in `meta3`.
- Lockup text: `lockup` (plan or slide), default ["FROM A","Creator","FOR A","Creator"].
- Logo on the hook: `logo` + `logo_mode` ("chalk" redraws a logo's white shapes in chalk; "silhouette"; "color").
- Full spec: `library/kits/carousel-kit/carousel/knowledge/style-chalk.md`.

### Sky-Blue specifics
- **All type is white.** The magenta→pink→orange gradient appears ONLY on the brush re-write of
  `hero_word` (one per slide) and in real brand logos — never in charts, frames or buttons.
- **Headline:** `headline` lines split with `|`; the last line is auto-fitted biggest. Choose the
  `hero_word` from line 1 — on the big last line the brush doubles up.
- **World:** `layout:"photo"` (default with `bg_file`) = full-bleed clear-sky photo with an automatic
  navy scrim; `layout:"field"` = navy #2C4E72. One different, credited photo per slide (`credit`).
- **Subject in front of the headline:** `subject_file` = cutout from `scripts/cutout.py` (aligned if
  same size as `bg_file`), or a trimmed cutout placed with `subject_box` {x,w,y|bottom}.
- **Logos:** `logo` + `logo_box` {x,y,w,rot,ry,frame} — `frame:true` puts the real logo on a silver
  device screen, as on the sheet. Never redraw it.
- Frames are thin white rules on deep navy; the CTA is an outlined frame, not a filled button.
- Full spec: `library/kits/carousel-kit/carousel/knowledge/style-skyblue.md`.

### Sun-Faded specifics
- **Faded gold is the headline only**; every other colour is sampled from the photo (credit = sky
  darkened, caption = ground darkened, hairlines = sky lightened). No panels, pills or buttons —
  data sits straight on the ground under a soft depth-of-field haze; the CTA is a caption line.
- **The headline sits behind the subject.** Pre-crop the photo to 4:5, run
  `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/cutout.py photo.4x5.jpg photo.4x5.cutout.png`, set `subject_file`.
  No cutout → the template sky-keys. Set `head_top` so the subject covers the lower part of the word.
- **Numbers are never hidden:** a numeric headline is auto-raised until no digit is >15% covered and no
  `. , % - $` is >2% covered; if it can't clear, the subject layer is dropped (logged `[sunfaded]`).
- If a sky-keyed slide shows any bite or speckle in the letters, don't ship it — use a photo with a clean
  clean cutout, or `subject_mode:"none"`.
- **Photos decide the slide:** one freely-licensed pastoral photo per slide — sky top third, one subject
  middle, calm open ground bottom third. Credit in `meta3`.
- Knobs: `head_top`, `head_width`, `rule1`, `rule2`, `ground_blur`, `ground_top`, `subject_mode`,
  `attribution`, `caption_alpha`. Logo: `logo` (PNG or SVG), drawn one-colour in the credit line.
- Full spec: `library/kits/carousel-kit/carousel/knowledge/style-sunfaded.md`.

## Shared tools for photo styles
- `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_photos.py <dir> "<search>" …` — freely-licensed Commons photos at 3840px
  (override with `CAROUSEL_PHOTO_WIDTH`), credits in `credits.json`.
- `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/cutout.py <photo> [<out.png>]` — subject cutout, free and local:
  rembg (if installed in the venv) or `npx hyperframes remove-background` (best on people).
  Same size as the photo, so templates stack photo → headline → cutout. Look at it on magenta first.
- Templates may read any slide/plan field via `__SLIDE_JSON__` / `__PLAN_JSON__`; `__SUBJECT__` and `__LOGO__`
  embed `subject_file` and `logo`.

## Reference — Midnight workflow (all local, all free)
1. **Init** — `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/carousel_run.py init "<topic>"` → a run folder + starter plan.
2. **Content** — write/verify the copy and the per-slide `content` blocks (below). Arc = hook →
   body (one idea/slide, ≥1 real screenshot or chart) → CTA. Keep to 5–7 slides.
3. **Scenes** — give each slide a `bg_scene` (see the table below) so neighbouring slides differ.
4. **Screenshots** — capture real charts/posts into `work/carousel-kit/shots/` (see "Screenshots").
5. **Build** — `library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/carousel_run.py build <run>` = paint backgrounds locally →
   render 1080×1350 PNGs → export to `work/carousel-kit/output/<slug>/`.
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

`library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/carousel_localbg.py --preview` renders one PNG per scene to compare.
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

## Logos (`library/kits/carousel-kit/carousel/scripts/fetch_logo.py`)
```
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py --list "<Company>"
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py work/carousel-kit/logos "<Company>" [--pick N --as <slug>]
```
SVG + transparent PNG from Wikimedia Commons, source/licence in `assets/logos/logos.json`. Check the
PNG is the current mark. Local path: place the file in the slide (mono in the style's type colour by
default; full colour only inside a card/chip). Paid path: upload the PNG as a second reference image
and name it in the prompt ("reference 2 is the official <X> logo — reproduce exactly, don't redraw").
See `library/kits/carousel-kit/carousel/knowledge/logos.md`.

## Screenshots (`library/kits/carousel-kit/carousel/scripts/capture.py`)
```
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/capture.py "<url>" work/carousel-kit/shots/out.png --selector "figure img"
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/capture.py "<url>" work/carousel-kit/shots/out.png --clip x,y,w,h --scale 2
```
`capture.py` is plain headless Playwright (no user-agent spoofing — removed on import), declines
cookie banners (reject/necessary only) and scrolls to trigger lazy content. Blocked sites: screenshot by hand.
- Find the region by listing large `svg,canvas,img,figure,table` blocks and reading
  `getBoundingClientRect()` + `window.scrollY`; `page.screenshot(clip=…)` clips *within the
  viewport*, so set a tall viewport before clipping below the fold, then clip at scale 2.
- Bot-protected / login-gated sites (e.g. X): use the interactive Claude Browser to find the
  region, then reproduce it with `capture.py`.
- Always set `caption` + `source`.

## Brand / look (`library/kits/carousel-kit/carousel/scripts/template.html`)
Void black `#08080A`, ash `#1A1B1E`, moon white `#FFFFFF`, bioluminescent teal `#3FBFB2`
(light only), ember amber `#E9A33C` (scene flora only), fog gray `#7C7C82`.
Headline + capsule = Cormorant Garamond Light; everything else = Inter.
The glass material is five CSS vars (`--glass-tint/-fill/-edge/-blur/-shadow`) — edit those and
every surface re-skins at once. Full detail in `library/kits/carousel-kit/carousel/knowledge/glass-and-brand.md`.

Alternate templates: `"template":"template-pastoral.html"` (the previous soft-pastoral look) or
`"template-90s.html"` (aged film). The style reference is
`library/kits/carousel-kit/carousel/assets/carousel-style-reference.png` — swap that ONE file to change the look.

## Optional PAID backgrounds (kie.ai) — only if the user asks
Put `KIE_API_KEY` in a `.env` at the project root, fill each slide's `image_prompt`, then
`carousel_run.py generate <run>` (Nano Banana Pro, 4:5, bundled reference as style input) →
`render` → `export`. Never spend credits before the user says go. Do NOT use any image MCP.
