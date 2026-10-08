---
name: carousel-generator-kie
description: >
  Generate a branded Instagram carousel (1080×1350, 4:5) from a style-reference image.
  AI (kie.ai Nano Banana Pro) paints the background; a code template lays crisp
  titles + data cards; and real web screenshots (charts, tweets, Reddit, YouTube) are captured
  and placed large in the middle. Two modes: Claude researches + captures the facts/screenshots,
  or the user supplies their own info/images. Use when the user asks to "make a carousel",
  "make an Instagram carousel", "turn this into a carousel", or "/carousel-generator-kie". PAID kie.ai path; the free path (own photos /
  plain sky field) is the default. Default brand Golfkuponger (@golfkuponger). Windows/content-engine import.
---

# Carousel generator — Soft Pastoral Editorial (kie.ai edition)

> **content-engine import.** Runtime: `library/kits/carousel-generator-kie/carousel/`; generated files
> go to `work/carousel-generator-kie/` (runs/, output/, shots/). Run scripts from the repo root with
> `library/.venv/Scripts/python`. **Free path (default):** `carousel_run.py build <run>` = render +
> export, with each slide's `bg_file` = your own photo (e.g. golf course photos) or no `bg_file`
> (plain sky field). **Paid path:** `generate` via kie.ai — needs `KIE_API_KEY` in the repo-root
> `.env` AND a public URL for the style sheet in `CAROUSEL_STYLE_REFERENCE_URL` (the original
> automatic upload of your files to catbox.moe / 0x0.st was removed). Never spend credits without
> an explicit "go". Brand defaults: handle `@golfkuponger`, brand `Golfkuponger` (`init "<topic>"
> --handle @x --brand "X"`).

Makes a scroll-stopping, **data-rich** Instagram carousel that stays perfectly on-brand across
every slide. Backgrounds are AI (unique per slide, same world); all text + charts are code-rendered
(sharp, editable); real screenshots from the web fill the middle as proof.

Self-contained in `carousel/`. Needs one `KIE_API_KEY` in a `.env` (the user's kie.ai key).

## Golden rules
- **Titles are code, never AI.** AI garbles text. The model paints the background ONLY.
- **The middle must carry proof** — a chart, a stat, or a real screenshot. Never leave it empty sky.
- **Real screenshots get a source caption** (e.g. "via anthropic.com"). Always attribute; only use
  content the user has the right to repost.
- **Approval gate:** never run paid generation (the `generate` step / kie images) until the user
  approves the plan. `render` / `export` / screenshot capture are free.
- **Facts:** if researching, verify from a primary source (web search + fetch). Never invent numbers.

## Setup (once)
```
library/.venv/Scripts/python -m pip install playwright pillow python-dotenv requests numpy && library/.venv/Scripts/python -m playwright install chromium
```
Drop the style reference at `library/kits/carousel-generator-kie/carousel/assets/carousel-style-reference.jpg`.

## Two modes (ask the user which)
1. **Claude researches** — Claude web-searches the topic, verifies facts, and captures the relevant
   real charts/screenshots itself.
2. **User provides** — the user gives the copy, numbers, and/or their own screenshots (drop images in
   `work/carousel-generator-kie/shots/`). Claude just lays them out.

## Workflow
1. **Init** — `library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/carousel_run.py init "<topic>"` → a run folder + starter plan.
2. **Content** — write/verify the copy and the per-slide `content` blocks (see below). Arc = hook →
   body (one idea/slide, ≥1 real screenshot or chart) → CTA. Keep to 5–7 slides.
3. **Backgrounds (PAID, kie.ai)** — after approval, fill each slide's `image_prompt`, then run
   `library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/carousel_run.py generate <run>`. This calls **kie.ai Nano Banana Pro**
   (model `nano-banana-pro`, needs the user's `KIE_API_KEY` in `.env`) with the bundled style
   reference and downloads each background + sets `bg_file` automatically. Do NOT use any image MCP.
4. **Screenshots** — capture real charts/posts and save to `work/carousel-generator-kie/shots/` (see "Screenshots").
5. **Render (free)** — `library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/carousel_run.py render <run_dir>` → 1080×1350 PNGs.
6. **Export (free)** — `library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/carousel_run.py export <run_dir>` → `work/carousel-generator-kie/output/<slug>/`.
7. Open the slides for review; also draft a caption + hashtags.

## plan.json — per slide
`index, role (hook|body|cta), topic_tag, headline, hero_word (halftone accent; "" hides),
subtitle (caption pill; drop it on slides that have a data card — it reads redundant),
image_prompt (background scene), bg_file, content` (below), `out_file`.

### content types (rendered by `carousel_render.build_content`)
- **hero** (big voxel mascot / illustration floating on the bg, fills ~55% centered): `{"type":"hero","src":"assets/mascots/voxel_coin.webp","caption":"key stat here"}` — pair with `"layout":"hero"` on the slide.
- **image** (real screenshot — the star): `{"type":"image","src":"assets/shots/x.png","caption":"…","source":"via anthropic.com"}`
- **bars**: `{"type":"bars","title":"…","unit":"%","items":[{"label":"…","value":43.3,"highlight":true}],"note":["…","Source: …"]}`
- **stats**: `{"type":"stats","title":"…","items":[{"value":"$5","label":"input"}],"note":["…"]}`
- **dial**: `{"type":"dial","title":"…","segments":["Low","Medium","High"],"on":[1],"left":"…","right":"…","note":["…"]}`
- **chips**: `{"type":"chips","items":["…","…"]}` (great for hook/CTA quick facts)

Prefer a **real screenshot (image)** for the "scoop" slides; use bars/stats when no clean screenshot
exists. Screenshots ~16:9 fit the middle band best; crop tall tables to their top ~6 rows so the card
fits above the footer.

## Backgrounds (kie.ai Nano Banana Pro — via the kit scripts)
Do NOT call any image MCP. Write each slide's `image_prompt`, then run
`carousel_run.py generate <run>`. Under the hood `carousel_generate.py` uses the style reference's PUBLIC URL
(`CAROUSEL_STYLE_REFERENCE_URL`; auto-upload removed), then per slide POSTs to kie.ai:
`{model:"nano-banana-pro", input:{prompt, image_input:[style_url], aspect_ratio:"4:5", resolution:"2K", output_format:"png"}}`,
polls, and downloads each background → sets `bg_file`. Needs `KIE_API_KEY` in `.env`.
Prompt rule inside `image_prompt`: "use the style sheet ONLY as color/mood/style reference … no text,
no UI, no panels" or it copies the sheet's own labels. Model is swappable via `CAROUSEL_MODEL`.

## Voxel mascot heroes (the "fills the middle" look)
Bundled cutouts live in `library/kits/carousel-generator-kie/carousel/assets/mascots/` (`voxel_hook.webp`, `voxel_coin.webp`, `voxel_dash.webp`,
`voxel_mascot.webp` — converted from 6 MB PNGs on import) — reuse them. Place on a slide with `"layout":"hero"` +
`content:{"type":"hero","src":"assets/mascots/voxel_coin.webp","caption":"<the real stat>"}`, or in a
corner via the slide's `mascot` field `{src,pos:right|br|bl,h}`. The template adds a grounding shadow;
keep real numbers in the caption. (To make BRAND-NEW mascots you'd generate a voxel character on kie
and cut out its background — optional; the bundled ones usually suffice.) Use real screenshots (not
mascots) for hard-data slides.

## Screenshots (`library/kits/carousel-generator-kie/carousel/scripts/capture.py`)
Capture real web visuals to a PNG:
```
library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/capture.py "<url>" work/carousel-generator-kie/shots/out.png --selector "figure img"
library/.venv/Scripts/python library/kits/carousel-generator-kie/carousel/scripts/capture.py "<url>" work/carousel-generator-kie/shots/out.png --clip x,y,w,h --scale 2
```
`capture.py` is plain headless Playwright (user-agent spoofing removed on import), declines cookie
banners (reject/necessary only), scrolls to trigger lazy content. Blocked sites: screenshot by hand.

**Finding the exact region** (charts are often `<img>`/`<svg>`, not text you can select):
- Load the page and list large blocks: for each `svg,canvas,img,figure,table` with width≥350 & height≥200,
  read `getBoundingClientRect()` (+ `window.scrollY`) → gives x/y/w/h in CSS px.
- `page.screenshot(clip=…)` clips **within the viewport**, so set a tall `viewport` height (≥ y+h) before
  clipping below the fold, then clip at scale 2 for crisp output.
- **Bot-protected / login-gated sites** (e.g. X/Twitter) that headless can't reach: use the interactive
  Claude Browser to load + find them, then reproduce the URL/region with `capture.py`.
- Always set a `caption` + `source` on the image content. Crop tightly to the chart.

## Brand / look (`library/kits/carousel-generator-kie/carousel/scripts/template.html`)
Palette (style sheet): sky `#8FBEDD`, cloud `#F7F4EE`, meadow `#7A9C4B`, blossom `#E7A3B6`,
terracotta `#CE6A4A`, charcoal `#2B2B2B`. Headline = DM Serif Display; accent word = Bevan (chunky
slab) with charcoal halftone dots + terracotta outline/shadow/sparkle; pills/cards = charcoal or
translucent cloud. Handle default `@golfkuponger`, brand mark `Golfkuponger` (plan `handle` / `brand_label`). Edit the CSS
vars/positions in `template.html` to restyle everything at once.
