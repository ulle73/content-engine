# Catalog map — reach for these before hand-building

The HyperFrames catalog carries **372 items** (≈205 components, ≈167 blocks). Most of
this style is already implemented there. **Search the catalog first, install, then
restyle with `assets/tokens.css`** — hand-build only what the catalog misses.

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
npx --yes hyperframes catalog --search "<term>"     # discover
npx --yes hyperframes add <name>                    # install into the segment folder
```

Every installed item ships with its own colours. **Retoken it immediately** — replace
its palette with `--mg-*` variables, set every lit edge to `--mg-stroke` with a
`--mg-glow-*`, and re-time it to the measured durations in `motion-grammar.md`.
An un-retokened catalog block is the fastest way to break the style.

---

## By pattern

| This style's pattern | Catalog items to start from |
|---|---|
| **Word build** (section title, one word at a time) | `per-word-rise` · `text-stagger` · `caption-weight-shift` · `line-by-line-slide` |
| **Slam headline** | `headline-slam` · `kinetic-type-swap` · `char-slam-explode` · `tracking-in` |
| **Bar wipe / highlight box** | `caption-highlight` · `inline-highlight` · `marker-highlight` · `caption-clip-wipe` |
| **Light leak flash-through** | `light-leak` · `organic-light-leak-overlay` · `flash-through-white` · `transitions-light` · `chromatic-radial-split` |
| **Whip between scenes** | `whip-pan` · `whip-pan-cut` · `transitions-push` · `directional-wipe` |
| **Glass tile** | `spotlight-card` · `tilt-card` · `ios26-liquid-glass` · `vfx-liquid-glass` · `macos-tahoe-liquid-glass` |
| **Node map / flow diagram** | `flowchart` · `flowchart-vertical` · `tracing-beam` · `constellation-hub` · `hw-pipeline` · `svg-line-draw-loader` · `svg-stroke-trace` |
| **Panel stack that re-fits** | `grid-card-assemble` · `stagger-lattice` · `spring-stack-shuffle` · `pull-back-reveal` |
| **Stat card + count-up** | `count-up` · `number-wheel` · `number-pop-in` · `social-proof-card` · `x-follow-card` · `mk-progress-stat` |
| **Conic progress ring** | `conic-progress-ring` · `star-rating-fill` |
| **Point stack over footage** | `staggered-fade-up` · `blur-in` · `line-by-line-slide` · `marker-checklist-card` |
| **Screen stage** | `browser-device-stage` · `device-frame-stage` · `ui-focus-zoom` · `yt-camera-move` · `scroll-camera-story` · `sticky-mock-swap` |
| **Cursor on a demo** | `simulated-cursor` · `oversized-cursor` · `cursor-glyph-trail` · `gesture-tap` · `press-ripple` |
| **Device splay / dive** | `multi-device-splay` · `parallax-device-dive` · `three-orbiting-cards` · `zoom-through-transition` · `split-tilt-cards` |
| **Camera moves on a stage** | `camera-rig-depth-stack` · `camera-dolly-zoom` · `push-in` · `parallax-zoom` · `parallax-unzoom` · `pan-stations` · `focus-rack` |
| **Persona circle / testimonial** | `testimonial-card` · `testimonial-proof-card` · `avatar-cloud` · `avatar-group-hover` |
| **Typed quote / name** | `typewriter` · `typed-prompt` · `streaming-text` · `notes-typing` · `scramble-reveal` |
| **Brand lockup / outro** | `logo-brand-close` · `logo-sting` · `cta-lockup` · `cta-close` · `logo-outro` · `store-badge-lockup` |
| **Lower third** | `lt-neon-border` · `lt-accent-underline` · `lt-dark-card` · `lt-mask-reveal` · `lt-kicker-name` · `yt-lower-third` |
| **Backgrounds** | `mesh-gradient-bg` · `aurora-drift` · `grain-field` · `grain-overlay` · `vfx-liquid-background` · `mk-background` · `vignette` |
| **Chart / data hit** | `animated-bar-chart` · `chart-story` · `data-chart` · `decline-chart` · `cut-the-curve` · `mk-line-graph` |
| **Terminal / code** | `code-terminal-run` · `terminal-simulator` · `code-typing` · `code-highlight` · `code-scroll` · `code-snippet-dark-2026` |
| **Real article / post / tweet** | `x-post` · `x-follow-card` · `reddit-post` · `yt-comment-card` · `news-ticker` · `ticker-takeover` |
| **Notification / message** | `native-notification-pop` · `notification-stack` · `notification-cascade` · `macos-notification` · `message-thread-reveal` · `chat-thread` |
| **Map** | `world-map` · `us-map` · `us-map-flow` · `spain-map` |
| **Emphasis / accent** | `gloss-sweep` · `light-sweep-pass` · `shimmer-sweep` · `text-shimmer` · `spring-pop` · `badge-pop` · `success-check` |
| **Grit / texture** | `motion-blur` · `chromatic-aberration-wipe` · `rgb-glitch-text` · `halftone-dissolve` · `scan-band` |

---

## Captions

The user's reference link was `catalog/components/caption-camera-follow` — worth
knowing what it is: one sentence written across a world far larger than the frame, each
word sized against everything already written, so the block grows geometrically while
the **camera pulls back at a steady rate** to keep landing each new word at the same
size. Old words stay lit and simply become small.

It is a striking effect and a legitimate choice for a **cold open or a single hero
statement**. It is *not* the running caption style for a long-form video — it takes the
whole frame and cannot share it with graphics.

For the running accumulating caption (⌁ REF-B), start from:
`caption-weight-shift` (the newest word lighter, already-said words bold — this is the
closest match) · `caption-highlight` (the magenta box on a key word) ·
`caption-pill-karaoke` · `caption-editorial-emphasis` · `caption-neon-glow`.

There are ~18 `caption-*` components; `hyperframes docs prompting/captions-catalog` maps
tone to component if you want to browse them.

---

## Workflow skills, not just blocks

All HyperFrames skills are installed. Relevant ones:

- **`talking-head-recut`** — the closest workflow to this skill: timed graphic overlay
  cards synced to a transcript, clip playing untouched underneath. Use its machinery;
  override its design with `tokens.css` and the scene list in `layouts.md`.
- **`motion-graphics`** — short design-led units (a stat hit, a logo sting, a chart).
  Use it to author an individual overlay, not the whole video.
- **`embedded-captions`** — the caption pass, including the 35-style catalog.
- **`media-use`** — BGM, SFX, icons, brand logos, TTS, transcription, background
  removal, colour grading. The single door for any asset.
- **`hyperframes-keyframes`** — punch-ins, camera moves, seek-safe 2D/3D keyframes.
  Read it before writing any camera move.
- **`hyperframes-animation`** — the motion rule set and scene blueprints.
- **`hyperframes-registry`** — installing and wiring catalog items.

The 3D character in ⌁ REF-B 0:35 is generated, not CSS. If a video wants one, generate
it via `media-use` / Higgsfield and treat the result as media — a rendered object on the
stage, not an animated element.
