# Captions — the core of PERSA

> *"same captions … it's close to his head, but his head always overlays the
> captions, but we're still able to read it."*

That sentence describes **two different things**, and conflating them is the
fastest way to get this style wrong. There are two text tiers, and they live on
opposite sides of the subject.

```
z 50   .pa-caption     one word, small, at 73% height   ── IN FRONT of the subject
z 40   .pa-subject     the matted talking head          ── the cutout
z 20   .pa-emph        one word, huge, at 25% height    ── BEHIND the subject
z 10   .pa-panel       media panels, screen recordings  ── behind everything
z  0   the graded plate
```

The **word caption** is in front. The **emphasis word** is behind, and the head
occludes its lower third — which is exactly why it reads as *placed in the room*
rather than stuck on the lens. Evidence:
`reference/stills/01-headline-behind-head.png` (the cap cuts the bottom off
"PLUGIN") and `05-emphasis-outline-word.png`.

---

## 1 · The word caption

Measured off `reference/stills/07-caption-4x.png` and `10-caption-hardcut-30fps.png`.

| Property | Value | Note |
|---|---|---|
| Content | **exactly one word** | never a phrase, never accumulating |
| Face | Inter 700, ALL CAPS | `--pa-font-caption` |
| Size | cap-height 38px @1920h → `--pa-cap-size` 2.75% | ≈53px font-size |
| Colour | pure `#FFF` | the only true white on screen |
| Position | centred, **73% of frame height** | measured 73.0 / 73.1 / 73.7 across three frames |
| Tracking | ≈ +0.015em | |
| Treatment | soft dark halo, no box, no stroke | `--pa-cap-halo` |
| **Transition** | **NONE. It hard-cuts.** | **0 frames** |

### ⭐ The caption hard-cuts. This is the rule people break.
Stepping the reference frame by frame at 30fps: "THE" holds 5 frames, then
"PROPERTY" is simply *there* at full size and opacity on the next frame, holds 16
frames, then "AND" for 4. No fade. No scale-in. No pop, bounce, blur or
typewriter. The word is replaced.

The shortest measured hold was **4 frames (133ms)**. Do not pad short words to a
"readable" minimum — the machine-gun cadence on fast speech is the texture.

`scripts/check-persa.sh` fails the render if it finds a transition, an animation
or a GSAP tween on `.pa-caption`.

### It does not move
Fixed x and y for the whole video. It does not track the speaker's mouth, it does
not shift for a long word, it does not reflow. When the layout changes to a
talking-head card, the caption stays at 73% of the **frame** — which puts it
inside the card, on the subject's chest. That is correct.

---

## 2 · Where 73% comes from

73% of frame height is roughly **chest level** on a seated medium shot. It reads
as "on the person" without covering the mouth or the hands, and it is far enough
from the bottom edge to clear a platform's UI. If a video is framed tighter or
wider, move `--pa-cap-y` so it lands on the chest — the *anchor* is the body, and
73% is what that measured to on the reference framing.

Never put it in a bottom band. That is a subtitle, and it is a different style.

---

## 3 · The emphasis word

One word per beat, promoted out of the caption stream to carry the point.

| Property | Value |
|---|---|
| Size | cap-height ≈153px @1920h → `--pa-emph-size` 11% (≈211px) — **4× the caption** |
| Position | centred, **25% of frame height** — behind the head |
| Face | `--pa-font-display` (Anton / Impact), ALL CAPS, tight |
| Default treatment | **outline only**, 6px stroke, in `--pa-amber`, with a glow |
| Variants | `--pa-emph--solid` (white, filled) · `--pa-emph--lime` |
| Z-order | **behind `.pa-subject`** — non-negotiable |
| In | blooms up over 5 frames (`--pa-dur-emph`) — it may animate; the caption may not |

Frequency: roughly **one per 8 seconds** in the reference. More than that and the
frame never settles; the emphasis stops meaning anything.

Pick the word that is the *claim*, not the loudest noun — the reference promotes
"MANUALLY", "AGAIN", "TIRED", "THING": the words that carry the frustration the
line is about.

### Why the occlusion matters
If the emphasis word sits in front of the head it reads as a lower-third graphic.
Behind the head, with the cap cutting into it, it reads as **set in the space the
person is in**. Same word, same font, completely different register. This is the
single technique most worth getting right in this style, and it requires the
matte — see `reference/layouts.md` §5.

Readability rule: at least **the top two-thirds of the letterforms must stay
clear** of the subject. If the head covers more than a third, raise
`--pa-emph-y` or shorten the word. "Still able to read it" is the constraint.

---

## 4 · The slam headline

The opener treatment. A hand-lettered line in `--pa-font-hand` above a huge
`--pa-red` display word, both **behind the matte**, both landing in 4 frames
(`--pa-dur-slam`). See `reference/stills/01-headline-behind-head.png`.

Used once, at the top, to state what the video is. Not a recurring device.

---

## 5 · Building them

```bash
python scripts/build-captions.py assets/transcript-tight.json \
    --out seg-01-cold-open/captions.html \
    --emphasis MANUALLY,AGAIN,TIRED
```

⚠ **`transcript-tight.json` is the only timing source.** The tighten pass moves
every word onset; timing against the original transcript shows up as "the
graphics are all slightly early", never as an error.

⚠ **Ship a separate `.srt` as well.** Burned-in word captions are a style choice;
the `.srt` is the accessibility layer and they are not the same thing.
