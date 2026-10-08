# NextPhase LONG — Design System (16:9)

Everything here is HTML/CSS/SVG (HyperFrames-ready). AI video generation is used ONLY for the
~10% cinematic eye-candy — never for text, UI, or diagrams.

The house look for long form is **"Dark Dotted-Grid"** — warm-dark maroon→black with a subtle
dot grid and a coral edge glow. (The short's cream look is the 9:16 style; both palettes ship in
`tokens.css`, and a video can be built cream by swapping the root class — but dark is the
default for 16:9 and cream should be a deliberate, stated choice, not a drift.)

---

## Design tokens

### Color
```
/* Brand (shared with the short) */
--coral:        #D97757;   /* Anthropic primary clay-coral — accents, marks, chart line */
--coral-deep:   #BD5D3A;
--coral-soft:   #E8A38A;

/* LONG — dark dotted grid  (the default) */
--dark:         #201512;   /* base */
--dark-2:       #140D0B;   /* vignette edge */
--dark-glow:    #3A2016;   /* corner glow toward coral */
--dot:          rgba(217,119,87,.16);   /* grid dots */
--on:           #F7F3EF;   /* text on dark */
--on-soft:      #B9A59C;   /* labels, secondary */
--panel:        #2A1C17;   /* cards/panels on dark */
--hairline:     rgba(247,243,239,.10);

/* SHORT — cream (available, not the default here) */
--cream:#F0EDE4; --cream-card:#EAE6DA; --paper:#F6F5F1; --ink:#191817; --ink-soft:#6B6660;

/* Terminal (both) */
--term-bg:#17140F; --term-prompt:#E0A15F; --term-text:#E7E2D7;
```

### Type
```
--font-serif:   "Fraunces", Georgia, serif;          /* display TITLES. 600–900, optical */
--font-display: "Instrument Serif", Georgia, serif;  /* Parallax captions */
--font-heavy:   "Montserrat", sans-serif;            /* captions + big stats. 300 / 900 */
--font-ui:      "Inter", sans-serif;                 /* labels, body, UI mockups. 400–700 */
--font-mono:    "JetBrains Mono", monospace;         /* terminals, code, data labels */
```

### ⇄ The 16:9 type scale — NOT the short's
A 9:16 frame is viewed on a phone held close; a 16:9 frame is viewed on a laptop or TV. The
short's 110px title and 72px captions are enormous here and read as a meme. Use:

| Role | 16:9 size | (the short's, for contrast) |
|---|---|---|
| Chapter / section title | `--font-serif` **86px** | 110px |
| Hero stat | `--font-heavy` 900 **150px** | 150px |
| Card headline | `--font-ui` 700 **40px** | 52px |
| Body / list row | `--font-ui` 500 **30px** | 38px |
| Caption (Parallax) | `--font-display` **96px** | 120px |
| Caption (Weight Shift / Highlighted) | `--font-heavy` **64px** | 84px |
| Label / kicker | `--font-mono` **22px**, `.18em` tracking, uppercase | 26px |
| Lower third — name | `--font-ui` 700 **34px** | — |
| Lower third — sub | `--font-mono` **22px** | — |

**Minimum legible size on a 1920-wide frame is ~22px.** Anything smaller does not survive
YouTube's compression at 1080p, let alone someone watching at 720p on a phone.

### Radius / shadow / spacing
```
--r-card:22px; --r-sm:12px; --r-pill:999px;
--shadow-card:0 24px 70px rgba(0,0,0,.45), 0 4px 14px rgba(0,0,0,.25);   /* deeper on dark */
--shadow-cam: 0 18px 60px rgba(0,0,0,.55);
--pad:96px;      /* the 5% title-safe margin. Generous margins = premium. Never crowd. */
--gutter:32px;   /* 12-col grid of 128px columns inside the margins */
```

### Motion
```
--ease-out:cubic-bezier(.16,1,.3,1);      /* primary entrance */
--ease-soft:cubic-bezier(.4,0,.2,1);
--ease-overshoot:cubic-bezier(.34,1.56,.64,1);
--dur-enter:600ms; --dur-exit:380ms; --dur-pop:180ms; --dur-draw:850ms;
--dur-whip:280ms;  --dur-chapter:600ms;   /* long-form transitions */
--stagger:80ms;
```
One idea on screen at a time · vary entrances · SVG paths draw with `stroke-dashoffset` ·
numbers count up · never linear.

---

## The 16:9 frame

```
 0                                                             1920
 ┌──────────────────────────────────────────────────────────────┐ 0
 │  96px margin (title-safe)                                    │
 │   ┌────────────────────────────────────────────────────┐     │ 54
 │   │                                                    │     │
 │   │              CONTENT / LAYOUT AREA                 │     │
 │   │                                                    │     │
 │   │                                       ┌──────────┐ │     │ 738
 │   │  ┌──────────────────┐                 │  CAMERA  │ │     │
 │   │  │  LOWER THIRD     │                 │  BUBBLE  │ │     │
 │   │  │  96,830→1000,1000│   CAPTION BAND  │500×282   │ │     │ 830
 │   │  └──────────────────┘    y 890–990    └──────────┘ │     │ 1020
 │   └────────────────────────────────────────────────────┘     │ 1026
 └──────────────────────────────────────────────────────────────┘ 1080
```

- **Background:** `.bg-darkgrid` — radial `--dark-glow` top-left → `--dark` → `--dark-2`
  vignette, plus a dot-grid overlay (`--dot`, 30px spacing) masked toward the centre.
- The dot grid must stay **under** everything and never sit behind small text (it eats
  legibility) — the mask in `tokens.css` fades it at the edges for exactly this reason.

### The six layouts

| Layout | Geometry |
|---|---|
| **Full-Frame Face** | camera 1920×1080, edge to edge. Captions at `y~940`. |
| **Transparent Background** | RVM cutout on the designed BG; torso through a rounded-rect window. See `cutout-compositing.md` for the 16:9 geometry. |
| **Split — Media Left** | media `0–1150` (full height, `--r-card` on the right edge), face `1150–1920`. |
| **Split — Face Left** | the mirror: face `0–770`, media `770–1920`. |
| **Screen-Share + Bubble** | screen recording full-frame, camera bubble at `1364,738` (500×282, `--r-card`, `--shadow-cam`). See `screen-recording.md`. |
| **B-Roll takeover** | full frame, edge to edge, no camera. |

**⇄ Split layouts: the media half is a `--coral` block, full bleed.** Inherited from the
short's Half & Half rule and it still holds — the *half* is what gets highlighted, edge to
edge, with the media inside it on a thin ~40px margin. Do NOT put a coral frame around the
picture and call it a split; the split has to read as a split instantly.

### Caption styles

| Style | Look | Use it for |
|---|---|---|
| **Parallax** | `--font-display` (Instrument Serif), `--coral`, 96px, enters with a vertical stretch (`scaleY 2.8 → 1`) | the lines that matter — cold open, the turn, the close |
| **Weight Shift** | `--font-heavy`, weight 300 crossfading into 900 as the word lands, `scale .85 → 1` | ordinary narration, when captions are on |
| **Highlighted** | `--on` on a `--coral` marker sweeping in behind the word, 14px radius | split layouts, matching the coral half |

Word by word, always: one word, popping in on its own transcript onset, out, next. Never a
chunk with a moving marker. Assign styles **per beat** — "important" is a directorial call, not
something in the transcript.

⇄ Captions are **selective** in long form (see `SKILL.md` §1). Ship a separate `.srt` regardless.

### The lower third
The long-form element the short has no room for. Use it for: a person's name and role, a tool
name + one-line descriptor, a source citation under a stat, and the chapter label for the first
~4s of a chapter.
- Box `96,830 → 1000,1000`, left-anchored, `--panel` at ~92% with a 3px `--coral` left rule.
- Enters `clip-reveal` from the left (`clip-path`), sub-line staggered +80ms; exits `wipe-out`.
- On screen **3.5–5s**, never longer. Two lines maximum. `components/lower-third.html`.

### The chapter card
2s, full-frame, on the dot-grid BG: the kicker (`CHAPTER 02`, mono, coral), the title
(`--font-serif` 86px), and a coral rule drawing left→right underneath. The dot-grid wipes
across on entry. Always carries a `riser` tail or a `magic-reveal`.
`components/chapter-card.html`.

---

## AI-GEN eye-candy (~10%)
Abstract glowing coral/amber neural-energy shots over dark server fields; cinematic, slow, no
readable text or logos. Build ~15–20 clips ONCE (Higgsfield / Kling / Pexels / Mixkit) and reuse
across videos. **Never rely on it for anything specific.** 2–4s inserts only, and never in place
of a real resource — it is texture between proofs, not proof.
