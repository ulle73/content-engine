# Layouts

---

## 1 · The frame — MEASURED

At 1080×1920, everything on screen is one of three things: pure black ground,
one rounded window, one serif line.

```
   0 ┌──────────────────────────────────────┐
     │              #000000                 │
 360 │      the definition of ... :         │   title line, 56px, set once
 404 │                                      │
 476 ├──── 56 ──┬─────────────────┬── 56 ───┤
     │          │                 │         │
     │          │   968 × 968     │         │   the window. A SQUARE.
     │          │   r = 70px      │         │   radius 70px
1023 │          │  caption here   │         │   caption baseline y=1042
     │          │                 │         │
1443 ├──────────┴─────────────────┴─────────┤
     │              #000000                 │
1920 └──────────────────────────────────────┘

     476 + 968 + 476 = 1920      56 + 968 + 56 = 1080
```

**The symmetry is the whole gag.** The air above and below is equal to the
pixel. A window 8px off-centre does not read as a choice, it reads as a
mistake, and it is the first thing an eye catches on a frame this empty.

Three things follow from the ground being literally `#000000`:

- **No drop shadow on the window.** There is nothing behind it to catch one.
  It is invisible work that costs render time and nothing else.
- **No border, no rim, no glow.** The radius is the only edge treatment.
- **Nothing lives in the bottom air.** It is empty for all 40 seconds of the
  reference. No progress bar, no handle, no logo, no chapter dots. The air is
  the design; filling it is the most obvious way to break this style.

## 2 · The title line — MEASURED

One serif line in the air **above** the window, sitting low in it — 66px above
the window edge with ~360px of empty black above that. Centring it vertically
in the air breaks the balance; it needs to belong to the window.

**It is set once and never changes.** 80 frames sampled across the reference
diffed against frame 0 at a max of 1.8/255 — that is JPEG noise, not motion.
It does not animate in, does not animate out, does not update per beat.

For long-form, that means **one title line per chapter**, changing only on a
hard cut at a chapter boundary. Changing it mid-chapter is a different, busier
style. Sentence case, ending in a colon.

## 3 · The scenes

The reference is **one continuous locked shot for 39.9 seconds** — scene-score
detection over the whole file found nothing above 0.15, and a static background
edge sat at 0px drift throughout.

That is honest and it is the style, but 40 seconds is not 12 minutes, and the
house rule that the frame must never look the same for long still applies. So:

> **Scene 1 is MEASURED. Scenes 2–5 are DERIVED** — invented to give long-form
> a rotation without breaking anything that was measured. They keep the ground,
> the window geometry, the type, the stillness and the hard cut. If a second
> reel from this creator ever turns up, check these against it.

| # | Scene | Status | For |
|---|---|---|---|
| 1 | **Locked Window** | measured | the rest beat — and it is most of the runtime |
| 2 | **Media Window** | derived | the window holds the real resource instead of the face |
| 3 | **Split Window** | derived | the face and the thing, at once |
| 4 | **Title Card** | derived | the chapter break |
| 5 | **Full Bleed** | derived | the one move in the entire style |

### 1 · Locked Window
The plate fills the window. Caption on top. Nothing else. Hold it 6–15s at a
stretch — this style is *supposed* to sit still, and cutting away from it every
three seconds is the amateur read of it.

### 2 · Media Window
Same window, different contents: a screen recording, a real product UI, a docs
or pricing page, a repo card. **The window does not resize for the media — the
media is cropped to the window.** The title line names what is being shown. In
and out on a hard cut.

### 3 · Split Window
Two panes inside one window, `.zk-window--split`. **One outer radius and a hard
2px seam of ground.** Never round the inner corners: two rounded boxes side by
side is a different design language. The caption stays centred on the frame,
not on a pane.

### 4 · Title Card
The window goes empty — black, but still a window, still holding the frame's
shape — and the serif line carries the chapter. No caption. ~2s, with a sound.

### 5 · Full Bleed
The window opens to the full frame over 6 frames, holds a beat, snaps back.
The title line goes with it. **Once or twice in a whole video.** It is loud
precisely because nothing else here moves; use it three times and it is noise.

## 4 · Rotation, media and safe zones

- **Never the same scene twice in a row. Never hold one past ~20s.**
- Every scene change carries a sound. There is no visual transition to carry
  it — see `sound-design.md`.
- **≥1 real resource per 20s, minimum 8 in a long-form.** Real screenshots,
  real UI, real docs. Check each one actually rendered content: login-walled
  and JS-heavy pages come back blank and ship as empty windows.
- **No random humans as b-roll.** Cut to a person only when that person *is*
  the subject of the line.
- **Never use emojis.** There is no accent colour in this style to build a
  mark from — a designed mark here is white type, a white rule, or nothing.
- Re-encode every sourced clip to **30fps CFR** and verify with `ffprobe`.
- The window edge is the safe zone. Nothing renders outside it except the
  title line.

## 5 · 16:9 — DERIVED

The style was measured at 1080×1920. **1920×1080 is the studio default and
every token that moves is derived, not measured.** Put
`class="zk-frame zk-16x9"` on the composition root.

**The window stops being square.** A 9:16 frame can spend 55% of its area on
black because a phone is held at arm's length; a 16:9 video watched across a
room cannot. The window becomes a **2.35:1 scope letterbox, 1720×732**, with
the same 5.19% side margin as the reference and 174px of black above and below.

```
   0 ┌───────────────────────────────────────────────────┐
 113 │              what nobody tells you:               │  title, 46px
 174 ├── 100 ──┬───────────────────────────────┬── 100 ──┤
     │         │        1720 × 732             │         │  r = 70px (absolute)
 584 │         │      caption sits here        │         │
 905 ├─────────┴───────────────────────────────┴─────────┤
1080 └───────────────────────────────────────────────────┘
```

**This genuinely re-crops the source, it does not scale it.** `zak-plate.sh`
takes a `crop-y` for exactly this reason — a talking head almost always wants
0.30–0.40, throwing away headroom rather than chin.

Five tokens move and each has a reason:

1. **Window** → 1720×732 at y=174, for the arm's-length reason above.
2. **Radius** holds its *absolute* 70px (`3.65cqw`). At `6.48cqw` it would be
   124px on a 1920-wide frame and the window would read as a pill.
3. **Title** → 46px. `2.92cqh` would be 31px here and dies in compression.
4. **Caption y** re-derived against the *window*: 56.0% of window height, which
   lands at 54.07% of the frame.
5. **Caption size** → 80px, and this one was **chosen, not derived.** The
   window changed aspect, so the two candidate rules disagree by 3×: matching
   the caption's height against the window gives 48px and reads as somebody
   else's subtitle track; matching its width fill (the reference line spans 64%
   of the window) gives ~150px and swallows a 732-tall window. All three were
   rendered against a real plate and held beside the reference; 80px carries
   the same presence. **Change it by looking, not by arithmetic.**

6. **CAPTION Y is a per-shot decision here, and this one fails silently.**
   54.07% puts the caption at 56% of the window — over the *chest* in the
   reference, because that creator sits far back and their head is 28% of the
   window height. A normal 16:9 talking head fills 55-65% of it, and the same
   token lands **across the mouth**. No crop recovers the reference proportion:
   a 1080-tall source simply does not contain enough room above and below the
   head. Measure the collar, put the caption below the chin on the shirt, and
   set `--zk-cap-y` on the composition root. On a real medium shot that was
   **74%**. Verify with `check-contrast.py --cap-y 74`, not the default.

Everything else transfers unchanged: the ground, the symmetry, the type
pairing, the hard cut, the stillness, the empty bottom air.
