# NextPhase — Video Style Framework

One system, three looks. Everything here is HTML/CSS/SVG (HyperFrames- and Remotion-ready). AI video generation is used ONLY for the ~10% cinematic eye-candy — never for text/UI/diagrams.

## The three looks
1. **SHORT — "Cream" (Nick-Saraev × Anthropic).** Vertical 9:16. Cream background, serif display title, big black karaoke captions, a large talking-head card at the bottom (~half the frame — face reads big), ONE clean graphic in the top zone (terminal / task-list / chart / stat / mascot). *This is the uploaded reference.*
2. **LONG — "Dark Dotted-Grid" (Anthropic explainer).** 16:9. Warm-dark maroon→black background with a subtle dot grid + coral edge glow. Search-bar autocomplete, logo-arc diagrams, stat reveals. *This is the images you sent.*
3. **AI-GEN — cinematic eye-candy (~10%).** Abstract brain/compute/energy shots. Built once into a reusable library (Higgsfield/stock), reused across videos. Never contains readable text or logos.

---

## Design tokens

### Color
```
/* Brand (shared) */
--coral:        #D97757;   /* Anthropic primary clay-coral — accents, mascot, chart line */
--coral-deep:   #BD5D3A;   /* pressed/darker coral */
--coral-soft:   #E8A38A;   /* tints */

/* SHORT — cream */
--cream:        #F0EDE4;   /* page background */
--cream-card:   #EAE6DA;   /* cards / panels */
--paper:        #F6F5F1;   /* alt textured white bg (leaf-shadow variant) */
--ink:          #191817;   /* titles, captions, stats (near-black) */
--ink-soft:     #6B6660;   /* labels, secondary */

/* LONG — dark dotted grid */
--dark:         #201512;   /* base */
--dark-2:       #150E0C;   /* vignette edge */
--dark-glow:    #3A2016;   /* corner glow toward coral */
--dot:          rgba(217,119,87,0.14);  /* grid dots */
--on-dark:      #F7F3EF;   /* text on dark */
--on-dark-soft: #B9A59C;

/* Terminal (used in both) */
--term-bg:      #17140F;
--term-prompt:  #E0A15F;   /* amber prompt */
--term-text:    #E7E2D7;
```

### Type (all free Google Fonts — match the references closely)
```
--font-serif:  "Fraunces", Georgia, serif;      /* display TITLES (Anthropic-like). Weight 600–900, optical. */
--font-heavy:  "Montserrat", sans-serif;         /* KARAOKE captions + big STATS. Weight 900. (alt: "Archivo Black") */
--font-ui:     "Inter", sans-serif;              /* labels, body, UI mockups. 400–700 */
--font-mono:   "JetBrains Mono", monospace;      /* terminals, code, data labels */
```
Load: `https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600..900&family=Montserrat:wght@700;900&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap`

### Radius / shadow / spacing
```
--r-card: 22px;   --r-sm: 12px;   --r-pill: 999px;
--shadow-card: 0 20px 60px rgba(0,0,0,.12), 0 4px 14px rgba(0,0,0,.06);
--shadow-cam:  0 -12px 40px rgba(0,0,0,.10);
--pad: 64px;      /* generous margins = premium. Never crowd. */
```

### Motion (cinematic, never linear)
```
--ease-out: cubic-bezier(.16,1,.3,1);      /* primary entrance (expo-ish) */
--ease-soft: cubic-bezier(.4,0,.2,1);
Durations: enter 500–650ms · stagger 60–110ms · caption pop 180ms · line-draw 700–900ms.
Rules: one idea on screen at a time · vary entrances · hard-cut captions on the beat · SVG paths draw with stroke-dashoffset · numbers count up.
```

---

## SHORT layout (9:16, 1080×1920)
```
┌───────────────────────────┐
│  TOP ZONE  (0 – ~42%)      │  ← ONE graphic: title+stat+mascot / terminal / chart / task-list
│                           │
│      [ big graphic ]      │
│                           │
├───────────────────────────┤
│  CAPTION  (~43–49%)       │  ← Montserrat 900, black, 1–3 words, karaoke pop
│        a task             │
├───────────────────────────┤
│  CAMERA CARD (~50–100%)   │  ← your talking head (~half the frame), rounded-top card (--r-card), slight zoom
└───────────────────────────┘
```
- Background: `--cream` (or `--paper` with a soft leaf-shadow gobo image at ~6% opacity).
- Title: `--font-serif`, `--ink`, ~92px, two lines max.
- Stat: `--font-heavy` 900, `--ink`, ~110px, tabular-nums, count-up.
- Caption: `--font-heavy` 900, `--ink`, ~72px, one–three words, pops per phrase.
- Camera card: ~50% of the frame height (talking head reads large), rounded top corners only, `--shadow-cam`. (In HyperFrames this is your recording; in the kit it's a placeholder.)

## LONG layout (16:9, 1920×1080)
- Background: radial `--dark-glow` (top-left) → `--dark` → `--dark-2` vignette + dot-grid overlay (`--dot`, ~26px spacing).
- Search-bar block: centered rounded input (`--r-pill`) with a coral 1px border + soft coral outer glow; query types on with a blinking caret; numbered options fade/slide in staggered.
- Logo-arc block: two logo SVGs; an arc path draws (stroke-dashoffset) with a dot travelling along it; straight baseline for comparison.
- Titles: `--font-serif` on dark (`--on-dark`); labels `--font-mono` `--on-dark-soft`.

## AI-GEN eye-candy (~10%)
- Prompts aim for: "abstract glowing coral/amber neural energy over a dark server field, cinematic, slow, no text." Keep it dark + coral so it cuts seamlessly against both looks.
- Tools: Higgsfield (wired into this workspace) / Kling / stock (Pexels, Mixkit free). Build ~15–20 clips ONCE → reuse.
- Rule: never rely on it for anything specific (text, logos, UI). 2–4s inserts only.

## Build pipeline (cheap + automatable)
Script → Claude Code assembles HyperFrames comps from this component library (compose, don't animate from scratch) → drop camera + b-roll → VO (your camera, or ElevenLabs if faceless) → render. The library is built ONCE; every future video is composition.

## Where things live (this studio)
- `system/tokens.css` — the actual colors/fonts/eases. Import into every scene; never hardcode.
- `system/motion-grammar.md` — the animation behaviors + story devices (your creative layer).
- `system/editing-rules.md` — timing, safe zones, the no-linger rule, the timing table.
- `system/components/short-blocks.html` + `long-blocks.html` — live previews + brick source (open in a browser).
- Per-video work lives ONLY in `work/nextphase/videos/<folder>/VIDEO.md`. The system never changes.
