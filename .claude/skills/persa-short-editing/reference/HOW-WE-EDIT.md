> **PERSA SKILL NOTE.** This is a shared reference from the wider editing kit this skill was
> cut from. Where it talks about the cream plate, the house 4-frame rotation, the 3 caption
> styles / 4 caption bands, other styles (house, tierlist, vlog, yapping), `ui-blocks/`, the
> block picker, the storyboard tool or the registry shelf — those are not part of this skill.
> **`PERSA.md` overrides this doc wherever they disagree.** The rest (the clip contract, the
> matte, sourcing, rights, levels) applies as written.

# HOW WE EDIT — read this before touching a video

Written 2026-08-09 after a long build with Jad. Everything here was learned by shipping
something broken and being told so. Follow it and you skip a week of rejected cuts.

**The one rule that matters most: never call a cut done from a snapshot. Sample the rendered
mp4.** The preview path and the render path disagree, and the preview lies (see §1).

---

## 0 · The look

| | |
|---|---|
| Plate | **flat cream `--cream` (#F0EDE4)**. The graph-paper grid was tried 2026-08-07 and **rejected** 2026-08-08 — do not bring it back. |
| Camera | one framing for the WHOLE video (see §2). If two beats are framed differently, he notices immediately and calls it broken. |
| Captions | in the **820–940 band**. Never on his body. Style per beat, not one style throughout (§4). |
| CTA | the old one — logo chip + `COMMENT` / `"KEYWORD"` in Instrument Serif italic + arrow (§5). |
| Display type | FOUR roles beyond the captions — see `TYPE-ROLES.md`. They need a **photographic, darkened** ground, so they belong on FULL FACE and B-ROLL FULL beats, not on the cream plate. |

---

## 1 · The HyperFrames contract — the bug that cost the most

**Visibility is owned by CLIPS, not by GSAP.** Every timed element MUST carry:

```html
class="clip" data-start="..." data-duration="..." data-track-index="..."
```

Without those the framework paints the element for the entire composition. A first cut was
built with plain `<div>`s + GSAP opacity tweens: **every graphic and all 167 captions were on
screen for all 52 seconds.** The snapshots looked perfect because the preview path drives the
GSAP timeline; the render path drives clips.

Four more that each cost a render:

- **`tl.to()` is not seek-safe.** Overlapping `to` tweens on one property resolve wrong when
  the timeline is seeked, and `fromTo` immediate-renders its `from` at build time. Use
  `tl.set()` for state changes, `fromTo` for motion.
- **A `<video>` nested inside a timed element renders FROZEN.** The wrapper must be plain;
  the video itself is the clip, and it needs an `id`.
- **Overlapping clips on one track conflict.** Give each concurrent element its own
  `data-track-index`. Captions alternate two lanes so neighbours never share one.
- **A full-frame takeover must suppress the camera clip**, or he ghosts through the page.

Register as `window.__timelines["main"]` with `data-composition-id="main"`.

---

## 2 · The camera — one framing, always

### The pop-out (the house look)
Head above a rounded card, torso inside it, on cream. **Mid-head cut.**

```
seam invariant:  RECT_Y − CROP_Y == PERSON_Y
this recording:  RECT_Y=1354  CROP_Y=974  PERSON_Y=380   → head top ≈ 1101
```

**Matte the WHOLE video, not just the transparent beats.** Three spans matted separately gave
three different framings and he called it "dog shit… why are they different". 1551 frames is
~6 minutes at 0.22 s/frame. Then composite ONE pop-out and use it as the base for every beat.

Only the full-screen FACE beats use the raw recording.

**Alpha haze:** RVM at `downsample 0.4` leaves ~0.06 alpha above the hair — the plate shows
*through his curls*. Floor it:

```python
a = np.clip((a - 0.18) / 0.82, 0, 1) ** 0.85     # 19,985 → 6,204 haze pixels
```

Do **not** drop to `downsample 0.25` — it is 7× worse, already measured.

**Do not delete the pop-out.** It was removed once because of a seam artifact; that threw away
his format. Fix the artifact, keep the pop-out.

### The plain card (older videos)
`object-fit:none; object-position:-40px -893px` — the source's own pixels at **1:1** from
y=893, in a 1000×1027 box at (40,893). Scaling the whole frame into the card crops his head
off. This is what the shipped videos do.

---

## 3 · Blocks must be VIDEO, never stills

Every block in `broll-library/ui-blocks/` is CSS-animated and accepts `?seek=<s>`.
A single screenshot of one is **not** an animation, and he will say so:

> "it looks like you just take a screenshot… but all of them have animations"

```bash
python scripts/block-render.py "skills-beat.html?mode=slash&fit=half" out.mp4 \
    --start 1.2 --dur 3.0 --fps 20 --width 1000 --height 880 --jobs 6
```

Shoots one headless frame per timestep in parallel (~2.9 s each, 6 at a time) and assembles at
30 fps CFR. 68 frames ≈ 36 seconds.

- **Watch the loop boundary.** Blocks loop at `--T` (6 s). A span crossing it snaps back to the
  push-in phase mid-beat. Pick a window inside one phase.
- **`?fit=half` is a RE-LAYOUT, not a scale.** For the 1000×880 coral half: camera move
  removed (no room to push), type sizes down, content re-anchored, the folder's fan arc rebuilt
  at half scale. A shrunk 9:16 block reads as a screenshot.

---

## 4 · Assets are chosen by MEANING, not by slot

The worst note he gave: a GitHub repo card with usernames on it while he was talking about
**sessions**.

> "why do I see git hub and like names like Brian or van? It makes no sense… if we're talking
> about sessions you can show the mascots controlling multiple sessions"

**Read what the line is about, then pick.** `library/index.json` maps concepts → asset pools,
keyed on what he actually says. Mined from 21 scripts:

| what he says | count | in videos |
|---|---|---|
| agent | 24 | 8 |
| model | 21 | 8 |
| free | 18 | 11 |
| prompt | 12 | 8 |
| Claude | 10 | 6 |
| **GitHub** | **3** | 2 |

Brands are a thin second layer. If a pool has nothing that fits, **go find it on the web** —
do not substitute something that is merely available.

`sessions-hub.html` exists because of this note: `?mode=talk` (one session messages another),
`?mode=hub` (a conductor wired to mac mini / laptop / desktop), `?mode=solo` (waiting).
Mascots *are* the sessions — no one needs the word explained.

---

## 5 · Captions

One word at a time, on its own transcript onset. **Style assigned per beat** — a directorial
call, not one style for all 167 words.

| style | what it is | use |
|---|---|---|
| **Parallax** | **Instrument Serif**, `--red`, entering on `scaleY 2.8 → 1` | hook, payoff, close |
| Parallax × gradient | same, with a coral→red ramp through the letters | emphasis lines |
| Weight Shift | Montserrat 300 crossfading into 900 | narration |
| Highlighted | white on a coral marker | every Half & Half beat |

Parallax **must** be Instrument Serif. Rendered in a bold sans it does not read as Parallax and
he will spot it.

**Chrome is DELETED — 2026-08-20.** *"I never want to see it ever again, turn it into
Parallax."* Silver needs a dark ground; on a light shirt and a light wall it disappeared
(tp-0817 @ 15.0s, and three sampled points on tp-0817b). **Face beats are Parallax at
y1400.** The style was removed from every `build.py` and every `index.html` in the corpus so
a rebuild cannot resurrect it. There are now THREE caption styles, not four. BLACKLIST #15.

**Position: the 820–940 band.** `y1400`/`y1500` land on his chest once the camera card is in
frame. Face beats are the exception — the whole frame is him.

### The old CTA (from `buzz`, `carousels`, `mcp`)
Half & half. Cream half holding a `.ctacard` — cream-card pill, product mark, product name in
mono — then `COMMENT` and `"KEYWORD"` in Instrument Serif italic (the keyword on a
coral→`--term-prompt` gradient), then a plain ink arrow. Do not invent a new one.

---

## 6 · Density — gaps, not averages

```bash
python scripts/check-density.py videos/<slug>     # or --all to back-test
```

Fails on **gaps**: warn > 4 s, fail > 6 s with nothing changing.

Measured across 21 shipped videos: the cuts that feel alive hold their worst gap at
**5.3–6.3 s**; the dead ones are all above 10. A cut with the **highest** graphics-per-minute in
the whole corpus still felt empty because of one 10-second hole. **19 of 21 shipped videos fail
this gate** — that is deliberate, it is a raise in standard.

**The gate cannot tell a screenshot from an animation.** Passing it with 13 stills is gaming it.
Density AND motion, or it is a slideshow.

---

## 7 · Sound

**Fixed cues, every video:**
- `swell` at **0:00** and on **every layout transition** — cut from Jad's own track
- `riser` into the hook
- `camera-shutter` on **each spoken part** of a platform name — OpenAI → 2 hits ("Open", "AI"), GitHub → "Git", "Hub", Claude Code → "Claude", "Code"
- bed = **`bgm/house-bed-loop.m4a`** — *Baba*, Daniel Deuschle, cut **0:09 → 0:45 and LOOPED**,
  so it never reaches the vocals and covers a video of any length. Lay it with
  `bash scripts/lay-bed.sh out/<slug>-sfx.mp4 out/<slug>-FINAL.mp4`.
  **Pre-levelled to −34 LUFS**, mixes at `volume=1.0`. Level the bed by LOUDNESS, never by peak:
  the old "−38 dB peak" put it at −49.8 LUFS and the music was inaudible. (2026-08-10.)
- `highlighter` on every marker sweep — a **real recording he supplied**, not synthesised

**Levels:** SFX 13–15 dB under voice peaks. Gains of 0.085–0.125 measured as **+0.5 dB** at the
cue — inaudible. Use **0.20–0.30**; verify by measuring the delta at each cue against the
visual-only render, do not assume.

`swell` came from the same track as the bed, so it doubles that bassline briefly. Inaudible at
−38; re-check if the bed is ever raised.

`chime` was explicitly deleted. `vinyl-rewind` is retired — the file stays only because 28 cues
across 16 shipped videos reference it and `mix-sfx.sh` hard-fails on a missing sound.

---

## 7b · What `halo-3-ai` and `ai-seems` taught (2026-08-11)

Two videos built back to back. Everything below is a note he gave, or a trap that cost a rebuild.

### The library comes first, and "adjacent" is not "right"
`ai-seems` is Claude Code end to end, and it still went to the web first. Then:
`sessions-grid` was used for "start a new session" and rejected — it draws **generic terminal
cards**, not Claude Code. **If he names a product, the asset must be recognisable AS that
product**: its banner, its mark, its chrome. Run
`python scripts/build-block-picker.py --all` before you open a browser. Full doctrine in
`SOURCING.md` §0b.

### Retype a block, never fork it
Blocks carry the copy of the video they were built for. `skills-beat` typed `/skills`;
`claude-new-chat` typed an Instagram reel URL. Both now take `?cmd=` / `?menu=` / `?prompt=`.
Changing the text in place is one parameter; forking is a second file that drifts. **Only real
product copy** — invented UI text is a fabricated interface, so look the string up.

### It is NEVER "a fetch video" or "a library video" — it is per beat
Corrected by Jad 2026-08-11, on exactly this mistake:

> "it's okay if sometimes the words are things we never mentioned there are things you can use
>  the library but it needs to make sense to what I'm talking about"

A product we have never covered does NOT mean everything must be fetched. `27b` is about
Bonsai 27B, which we had never touched — and the right answer still included **library and
registry blocks**: a phone frame with the real app UI in its screen slot, a device dive, the
logo blur-reveal. The web supplied the receipts (the licence, the file sizes, the app listing);
the blocks supplied the phone.

**Decide per BEAT, never per video.** For each line ask "what makes sense for what he is
saying?" — sometimes a real page, sometimes a block, often both in the same cut.

And the block pool is bigger than `broll-library/ui-blocks/`. **`npx hyperframes catalog` is
358 entries**, including a whole device family:
`device-frame-stage` and `browser-device-stage` (a phone/browser with a **screen slot** you
drop real UI into), `parallax-device-dive` (the camera pushes through a phone screen),
`vfx-iphone-device`, `ios26-liquid-glass`, `app-showcase`, `multi-device-splay`,
`screen-flow-carousel`, `notification-pileup`. Install with `npx hyperframes add <name>`.
Search it before concluding the library cannot cover something.

### The block loop boundary decides the beat length
Blocks loop at `--T` (6s). A beat that crosses the boundary snaps back to the push-in phase
mid-shot. `ai-seems` beat 06 is **exactly 6.00s** for that reason — the beat map was bent to
fit the block, not the other way round.

### A cue that REPEATS is texture
`highlighter` at the +2..+5 dB target measured +3.5..+6.0 and was rejected: *"we need to reduce
the highlighter sound more."* It fires on every marker sweep — six times in 48s. Anything firing
three or more times targets **+1 to +3 dB** (`highlighter` ≈ 0.34). One-off reveals keep the
higher band. See `sound-design.md`.

### Fact-check the script BEFORE the beat map, and let the picture carry the fix
`halo-3-ai` claimed "Artificial Analysis ranked it number one for video with audio". True only
of the **Video Editing** board; it is #2 on text-to-video. Rather than re-record, the cut puts
the Video Editing board on screen so the picture scopes the claim. **The asset choice can make a
loose line true** — but only if you find the problem before the beat map is built around it.
The ASR is the other half of this: "Halo 3" was **Hailuo 3 / MiniMax H3**, "slash status line"
was **`/statusline`**. Fix the caption text, never the timings.

### Stills of a terminal are a compromise, and he should be told
`concepts.json` says a terminal must be real AND animated. `ai-seems` ends up using two real
Claude Code stills with a slow push, because he chose the real UI over a built block. That is a
legitimate call — but say plainly that a still meter cannot drain while the VO says it is
running out, so the trade is visible.

## 8 · Sourcing

**Three sourced sightings per short — hook, middle, near the end.** The first one rides
**above his head in the Transparent opener**, so the real thing is on screen while he names it.
And only fetch what the library does not already have: Claude Code / ChatGPT / Gemini / sessions
/ skills all have blocks — a new tool (Kimi, Hermes, some product we have never covered) is what
sourcing is actually for. Full doctrine in `SOURCING.md`.


- **Article screenshots are unreadable because of arithmetic.** A 1400px-wide page in a 1080
  frame scales type to **0.70×**. Crop to the one story or the one headline and it scales
  **1.15–2.33× UP**. Never the whole page.
- Chrome headless renders raw text in **dark mode** by default — pass
  `--blink-settings=preferredColorScheme=1` or a multiply highlighter is invisible.
- GitHub forces its own dark theme regardless of that flag.
- `curl opengraph.githubassets.com/1/<owner>/<repo>` — 44 kB, instant, always current.
- Founder clips: `yt-dlp --download-sections`, ~500 kB for 6 s. **Probe then commit** — you
  cannot blind-pick a timestamp and get the right face; grab 2 s at four points, look, then
  download the one you want.
- Normalise every sourced clip to 30 fps CFR.
- Mac screenshot paths contain a **narrow no-break space (U+202F)** before AM/PM — glob, never
  a literal path.

---

## 9 · The library

`LIBRARY.html` at the repo root is the master index, generated from disk so it cannot drift.
242 assets: 24 mascot animations × 3 cuts (outline / tight / original), 6 live UI blocks,
15 brand marks, 10 real UI crops, 16 sound cues, 3 bed levels, 7 registry blocks,
9 registry components, 87 remocn components, and 22 move sections in
`broll-library/PREVIEW.html`.

Use the **outline** mascot cut — a cream sticker border that survives any plate.

Other pages: `UI-PREVIEW.html` (the 87 remocn components, after the catalog-wrapper fix),
`SOUNDS.html`, `EDIT-PLAN.html` (the beat-by-beat format), `catalog/index.html`.

---

## 9b · What was added 2026-08-10

- **`reference/BLACKLIST.md`** — the hard list. No small text in any form, no caption background
  bands, no webcam bubbles, and the rotation is a change of CAMERA TREATMENT not of graphic.
- **`library/concepts.json` → `CONCEPTS.html`** — 14 concepts mined from all 22 scripts, each with
  trigger words, a Show, a Never and live previews. `python scripts/build-concept-catalog.py`.
- **`ui-blocks/sessions-grid.html`** — real session windows (`babysit` / `parallel` / `approve`).
  Use this, not `sessions-hub`, whenever the line is about sessions: sessions-hub uses mascots AS
  the sessions and he rejected that.
- **`ui-blocks/page-highlight.html`** + **`scripts/shoot-page-9x16.py`** — the highlighter, rebuilt.
  A page is shot as a true 9:16 frame at ~640 CSS px (type scales ~1.7x UP), the phrase is located
  from the live DOM (one bar per wrapped line), the marker is opaque ink, the push zooms INTO the
  marker, and there is NO browser chrome. **One highlight at a time.**
- **`reference/SOURCING.md`** + **`scripts/fetch-source.py`** — where to fetch from, in priority
  order, and the contact sheet that makes you look before you commit.
- **`scripts/build-storyboard.py`** — a beat-by-beat STORYBOARD.html per video: real frames, arc
  role, the line, caption style, sound cues. Show him this BEFORE rendering.
- `scripts/block-render.py` gained `--bg` (render a block straight onto the coral half) and no
  longer silently truncates a video when Chrome drops a frame.

## 10 · Working with Jad

- **Show, do not describe.** Build the page or the frame and put it in front of him.
- **Look at your own output before shipping it.** Most rejected cuts were things I never opened.
- He will tell you precisely what is wrong, per timecode. Take it literally.
- Never publish without explicit approval.
