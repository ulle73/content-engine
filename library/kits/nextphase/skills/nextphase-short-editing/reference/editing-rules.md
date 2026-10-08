# Editing Rules — timing, safe zones, exits

These rules exist to fix the recurring problems: graphics covering the face, graphics staying on long after the point is over, and inconsistent timing. Follow them exactly.

## 1. Everything is bound to the transcript (no eyeballing)
- Work from `assets/transcript.json` (word-level timestamps). Every graphic has an **IN word** and an **OUT word**.
- **IN** = the onset of the word where the point/visual reference begins.
- **OUT** = the onset of the word where the point ends, plus a **0.3s tail**. Then it exits.
- Anchor to real word onsets, never to script timecodes (the recording is improvised).

### Transcript quality check (mandatory, once)
After transcription, read it. If >20% of tokens are `♪`/garbled, re-run at a larger model. Strip music/filler tokens before timing captions.

## 2. The no-linger rule (this is the big fix)
- A graphic lives **only for the clause/point it supports.** When I stop talking about the $300 story, the $300 graphic is already leaving.
- **Hard cap: 6 seconds** on screen for any single support graphic unless it's an intentional persistent element (e.g. a running caption track). If a point runs longer, evolve the graphic (add a layer) rather than letting a static one sit.
- **Every graphic MUST have an entrance AND an exit.** No orphan graphics that just pop and never leave. Exit ≈ `--dur-exit` (380ms), usually the reverse of the entrance or a soft fade+move.
- **One idea on screen at a time.** Before the next graphic enters, the previous one has begun (or finished) its exit. Never stack two unrelated supports.

## 3. Safe zones (this is the "don't cover my face" fix)
### LONG (16:9, 1920×1080)
- My camera is bottom-center → bottom-right during screen-share, and full-frame during hook/CTA.
- **Keep all graphics OUT of the bottom band (y > 800) center-and-right (x > 640).** Graphics belong top, left, and upper-right.
- During full-camera moments (hook, story beats, CTA): overlays may use the upper 55% and the far margins; use frosted panels/text-shadows so text reads, and still avoid my face (center).
- Screen-share sections: overlays are **small callouts/labels only** — never a full-screen card that hides the screen or the camera bubble.

### SHORT (9:16, 1080×1920)
Three fixed lanes (see `design-system.md`):
- **Top zone (0–800px):** ALL graphics live here.
- **Caption band (820–940px):** reserved for the karaoke caption. Nothing else.
- **Camera card (960–1920px, ~50% of the frame):** my face — sized large so I read big. **Never** place a graphic here.

## 4. The timing table (produce this, get "go" before rendering)
For every cue, output a row and show me before you build the final render:

| # | IN (word @ t) | OUT (word @ t) | Dur | Element / brick | Zone | Enter → Exit |
|---|---|---|---|---|---|---|
| 1 | "banned" @ 0:03.2 | "worldwide" @ 0:07.0 | 3.8s | headline slam | top | rise → fade-up-out |
| 2 | "$300" @ 0:11.5 | "minutes" @ 0:14.1 | 2.6s | cost count-up | top | scale-in → shrink-out |

Rules the table enforces: no row longer than 6s; no two rows overlapping in the same zone; every row has enter+exit; nothing in a reserved lane.

**SFX are a separate pass — not planned here.** This table is graphics only. Sound goes on *after* the visual edit is locked and rendered, placed against the real animation timings (see `system/sound-design.md`). Don't guess cues from the plan.

## 4b. Caption style follows the LAYOUT (not the beat)
- **Half & Half, either direction → HIGHLIGHTED captions.** Active word on a `--coral` marker block, `--cream` text, radius 14px. Animation Up → band `820–940`. Face Up → band moves to the seam `~985`, just under the face.
- **Transparent Background → default captions**, riding high above the head (~`y300`) on a soft scrim.
- **B-Roll → default captions BELOW the media** (~`y1420` letterboxed). Never overlay the b-roll.

## 4c. The rotation (retention)
Open **Transparent Background** 3–4s → **B-Roll** (web) → **Half & Half Animation Up** → rotate. Never the same layout twice in a row; never hold one past ~8s; every change carries a transition **and** a sound.

## 5. Pacing defaults (consistency)
- Captions (short): 1–3 words, swap on the beat, ~0.6–1.4s each. Always on screen.
- Support graphics: enter 500–600ms, hold, exit 380ms. Stagger internal elements by 80ms.
- Transitions between sections: 200–400ms (whip-pan / flash / dissolve — vary them).
- Numbers count up; SVG paths draw on; lists stagger in. Never let a chart or list appear instantly.

## 6. Render gates
`lint` → `inspect` (fix overflow / safe-zone violations) → `preview` (watch for lingering graphics) → render `--quality high --fps 30`. If a graphic in preview outlives its OUT word, it's a bug — fix before render. **Then the sound pass** (`system/sound-design.md`): `mix-sfx.sh` the SFX onto the locked render — present and varied, clearly heard but under the voice; if an effect buries a word, drop its gain.
