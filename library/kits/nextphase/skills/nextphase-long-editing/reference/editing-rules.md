# Editing Rules — timing, safe zones, exits (16:9)

These exist to fix the recurring problems: graphics covering the face, graphics staying on long
after the point is over, inconsistent timing, and — long form's own failure mode — a middle
section that quietly turns into eight minutes of talking head. Follow them exactly.

---

## 1 · Everything is bound to the TIGHT transcript

- Work from `assets/transcript-tight.json` (word-level, post-tighten). Every graphic has an
  **IN word** and an **OUT word**.
- **IN** = the onset of the word where the point or visual reference begins.
- **OUT** = the onset of the word where the point ends, **plus a 0.3s tail**. Then it exits.
- Anchor to real word onsets, never to script timecodes — the recording is improvised.

### The tighten pass comes first (long form only)
`scripts/tighten-cuts.py` removes dead air and shifts **every** onset. Run it before you time
anything. After it, the original `transcript.json` is dead — do not read from it again.
The script writes `assets/cuts.json` (the kept spans) so the remap is auditable.

### Transcript quality check (mandatory, once)
Read the transcript after transcribing. If >20% of tokens are `♪`/garbled, re-run at a larger
model. Strip music and filler tokens before timing.
**Gap-check minute by minute** — compare transcript span against file duration. A silently
dropped chunk in the middle of a 15-minute file desyncs everything after it, and checking only
the ends will not catch it.

---

## 2 · The no-linger rule

- A graphic lives **only for the clause it supports.** When the point moves on, the graphic is
  already leaving.
- **Hard cap: 10 seconds** for any single support graphic (the short's cap is 6s; long form can
  hold a beat longer, but not indefinitely). If a point runs longer, **evolve** the graphic —
  add a layer, advance a step, count something — rather than let a static one sit.
- **Every graphic MUST have an entrance AND an exit.** No orphans that pop and never leave.
  Exit ≈ `--dur-exit` (380ms), usually the reverse of the entrance.
- **One idea on screen at a time.** The previous graphic has begun its exit before the next
  enters. Never stack two unrelated supports.

## 3 · The long-form pacing floor (this is the big long-form fix)

A short cannot go stale in 45 seconds. A 15-minute video can go stale in ninety. Enforce:

| | limit |
|---|---|
| New visual beat | ≤ **8s** |
| Uninterrupted talking head, nothing changing | ≤ **12s** |
| Same layout | ≤ **25s** |
| Re-hook | ≤ **90s** |
| Silence between words (post-tighten) | ≤ **0.55s** |

If a stretch of the recording genuinely has nothing to show — flag it in `PLAN.md`. The honest
options are to cut it, cover it with a designed explainer, or accept a face-only stretch and say
so. Silently letting it run is what loses the viewer.

## 4 · Safe zones (the "don't cover my face" fix)

**Canvas 1920×1080. Margin 96 × 54 (title-safe). Nothing outside it, ever.**

| Layout | Where graphics may go | Reserved |
|---|---|---|
| **Full-Frame Face** | upper 55% and the far left/right margins, on a frosted panel or with a text shadow so they read | the centre — his face |
| **Screen-Share + Bubble** | anywhere except `x>1300, y>700` | the bubble `1364,738→1864,1020`; and **no full-screen card that hides the screen** — callouts and labels only |
| **Split — Media Left** | inside the media half, `0–1150` | the face half `1150–1920` |
| **Split — Face Left** | inside the media half, `770–1920` | the face half `0–770` |
| **B-Roll takeover** | the whole frame | — (captions drop clear of the media) |
| **Transparent Background** | anywhere clear of the head and shoulders | see below |

### The Transparent Background exception (the only one)
While that layout is on screen the safe-zone rules are **suspended** — the person legitimately
spans the frame, because they *are* the frame. Captions still run, placed clear of the head.
The instant it ends, the zones are back in force.

### Caption placement, by layout
- **Full-Frame Face** → centred, `y ~940`.
- **Screen-Share + Bubble** → centred within `x 96–1300` so it clears the bubble.
- **Split** → centred in the **media half**, `y ~940`, Highlighted style.
- **B-Roll** → clear of the media: below it if letterboxed, on a scrim at `y ~980` if full-bleed.
  **Captions must never overlay the b-roll.**
- **Transparent Background** → clear of the head, on a soft scrim.
- **Never put captions behind the cutout** — at chest height the body occludes the word entirely.
  This was tried and rejected.

## 5 · Pacing defaults

- Support graphics: enter 500–600ms, hold, exit 380ms. Internal elements stagger 80ms.
- Layout transitions: whip-pan 280ms · chapter wipe 600ms · dissolve 300ms · flash 1–2 frames.
- Numbers count up. SVG paths draw on. Lists stagger. **Never let a chart or list appear
  instantly.**
- Screenshots get a slow Ken-Burns (scale `1.00→1.06` over their whole life) — a static
  screenshot held for 8s is dead air with a picture on it.

## 6 · Render gates (per segment)

`lint` (0 errors) → `snapshot --at <times> -o snaps` → **read the contact sheet and fix** →
`render --quality high --fps 30`. If a graphic in the contact sheet outlives its OUT word, it is
a bug — fix before render. Then concat (`assembly.md`), **then** the two sound passes
(`sound-design.md`) on the locked cut.

**SFX are not planned in the timing table.** Sound goes on after the visual edit is locked and
rendered, placed against the real animation timings — never guessed from the plan.
