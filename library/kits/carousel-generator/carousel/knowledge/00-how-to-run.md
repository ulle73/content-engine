# 00 — How to run (read this first, Claude)

This is the master flow for the Carousel Generator kit. When the user asks for a
carousel, follow this exactly. The user should do almost nothing.

**Default mode is LOCAL: no API, no key, no cost.** Backgrounds are painted procedurally
by `carousel_localbg.py`, text and glass are rendered by `template.html`. Only offer the
paid kie.ai path if the user explicitly asks for photographic AI backgrounds.

## Flow
1. **Read the knowledge base**: `glass-and-brand.md`, `structure.md`, `hooks.md`, `ctas.md`,
   `backgrounds.md`, `mascots.md`, `data-and-screenshots.md` (all in this folder). Apply them.
2. **No key needed.** Do not ask for a kie.ai key unless the user wants the PAID background path.
3. **Ask which style** (or infer it from the topic):
   - *Midnight Bioluminescent* — `template.html` + `"theme":"midnight"`, backgrounds painted locally.
   - *Archival Swiss Poster* — `template-archival.html` + `"theme":"archival"`, one real photograph
     per slide (see SKILL.md → Archival specifics; never reuse a photo across slides).
   Use only the matching bundled reference sheet; never mix the two.
4. **Ask the user 4 questions** and wait: (1) topic or full script, (2) research-vs-user-provides,
   (3) slide count 5–7, (4) @handle + footer tagline.
5. **Write the copy** (hook → body → CTA), build the plan, and **show it for approval**.
6. **Build it** — all free, all local:
   - `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_run.py init "<topic>"` → run folder + plan.json
   - Edit `plan.json`: per slide set `headline`, `hero_word` (the ONE glass capsule word),
     `subtitle`, `topic_tag`, `content`, `bg_scene` (see `backgrounds.md`), and on the CTA slide
     `cta_pill` / `cta_soft` / `microcopy`. Set `handle` + `tagline` once on the plan.
   - `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_run.py build <run>`
     (= `localbg` → `render` → `export`; nothing paid, nothing downloaded)
   - Show the user the finished images from `work/carousel-generator/output/<slug>/`.

   Repaint a background you don't like: change its `bg_seed` or `bg_scene`, then
   `carousel_run.py localbg <run> --force` and re-render.

## Optional PAID path (only on request)
`KIE_API_KEY` in a `.env` at the project root → fill each slide's `image_prompt` →
`carousel_run.py generate <run>` → `render` → `export` (or `produce` for all three).
Never spend credits before the user says go.

## Hard rules
- Titles are code-rendered by the template — never AI text.
- ONE reference sheet only.
- ONE glass capsule accent word per slide.
- Type is moon white or fog gray only; teal is light, never paint; amber only in the scene.
- 5–7 slides; one idea per slide; the middle of every slide carries a visual — never empty.
- Keep the top ~45% of every background unbroken black.
- Verify facts/numbers; attribute real screenshots ("via …").

## Plan fields (per slide)
`index, role, topic_tag, kicker, headline, hero_word, subtitle, content, cta_pill, cta_soft,
microcopy, bg_scene, bg_seed, bg_tweak, mascot, bg_file`.
Plan-level: `handle, tagline, brand_label, template`.
`content` types: `image` (screenshot), `hero` (big cutout), `line`, `column`, `dumbbell`,
`meter`, `bars`, `stats` (+`spark`), `dial`, `chips`. See `data-and-screenshots.md` for which to pick.
Alternate templates: `"template": "template-pastoral.html"` (the old soft-pastoral look) or
`"template-90s.html"` (aged film). Default is the midnight glass `template.html`.
