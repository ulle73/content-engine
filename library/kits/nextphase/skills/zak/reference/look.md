# The look

## 1 · The ground — MEASURED, and it is absolute

`#000000`. Sampled at seven points across 120 frames: `[0. 0. 0.]` every time.

Not `#0A0A0A`, not a near-black, not a gradient, not a subtle noise texture,
not a vignette. Pure black, so the window is the only lit thing in the frame.

Everything else in the style follows from that. There are exactly **two
colours**: black and white. No accent. No second accent. No tint on the type.
If a beat seems to need a colour, it needs a different *shot*, not a swatch.

## 2 · The plate — MEASURED, with a caveat

Read over 120 frames sampled inside the window with the caption band excluded:

| | Reading | What it means |
|---|---|---|
| Mean luma | **90** / 255 | genuinely low-key; the image sits dark |
| Floor (1st pct) | **24** | blacks are **lifted** — nothing crushes to the ground |
| Ceiling (99th pct) | **151** | highlights never approach white |
| Mids `B−R` | **−53** | warm, and much warmer than `persa`'s −18…−28 |
| Mids `G−R` | −33 | green also below red — the cast is toward amber |
| Saturation | mean 0.35 | not desaturated. This is not a faded film look. |

> ⚠ **These are readings of that ROOM. They are not a transform, and treating
> them as one produced a bad plate on the first real video.**
>
> The warmth in that table is a red cap, a beige door and a warm practical
> behind the speaker as much as it is any grade. Real footage arrives with its
> own cast — a real test source measured **B−R −31 on its own, ungraded**. Push
> −53 onto that and you get −50 and an orange, muddy image; pull a ceiling of
> 198 down to 151 and the highlights flatten into mud. Both happened.
>
> **Take the EXPOSURE from this table and leave the COLOUR alone.** Low-key
> mean, a lifted floor, a gentle highlight roll-off — those transfer. `B−R −53`
> and `sat 0.35` do not. A source with a genuinely bad cast gets a balance pass
> upstream (`persa/scripts/persa-balance.py` works unchanged), not a bigger
> curve here.
>
> And **look at it**. `check-contrast.py` gates legibility, which is the thing
> that fails silently — it cannot tell you the picture has gone muddy. Put a
> graded frame beside the ungraded source before you render 75 seconds of it.

The floor and the ceiling are the load-bearing pair, and they pull in opposite
directions from the usual instinct:

- **Do not crush the blacks.** At a floor of 0 the window's dark edges melt
  into the ground and the frame stops having a window in it.
- **Do not let a highlight bloom.** Every bright pixel is a place the caption
  could die, and the ceiling of 151 is what keeps that from happening.

```bash
bash scripts/zak-plate.sh assets/recording.mp4 assets/plate.mp4 16x9 0.35 plate
```

That reframes to the window and applies the curve. It gets a source into the
neighbourhood; it is not a calibrated transform, and it says so.

## 3 · The number that actually matters — MEASURED and gated

**The plate luma behind the caption held at 126, min 121, max 129, across every
one of 120 sampled frames.**

That stability is not luck and it is not cosmetic. The caption has no shadow
and no stroke (`captions.md` §2), so the plate is the *only* thing making white
type readable. The reference speaker sits in front of a mid-dark wall for the
whole take, and the caption band never brightens.

```bash
python scripts/check-contrast.py out/seg-01.mp4
```

Ceiling is 150. Above that, unshadowed white type stops reading — and it fails
silently: the render succeeds, the thumbnail looks fine, the words are gone.

**When it fails, fix the plate.** Re-grade that shot darker, reframe the window
onto a darker part of the source, or move the caption off that beat. A
`text-shadow` is fixing the wrong layer, and `check-zak.sh` fails the render
for it.

### The light fall-off — when the caption has to live on a bright wall
Moving the caption off-centre (a right-hand column, say) often lands it on the
brightest part of the room. Darkening the *whole* plate to rescue it takes the
face down with it and brings back the mud.

Instead, darken only that side: a smoothstepped black ramp over the graded
plate, zero where the subject is and ~0.45 at the frame edge. It reads as the
key light falling off, not as a scrim, and it is a normal grading move.

```python
x = np.arange(1920); t = np.clip((x - 760) / (1920 - 760), 0, 1)
alpha = (t * t * (3 - 2 * t)) * 0.46          # smoothstep: no visible onset
```
Overlay it after the curve, before the crop. Measured on a real bright wall:
the caption band went **143 → 107** against a 150 ceiling, with the face
untouched. Verify with `check-contrast.py --cap-y <pct>`.

## 4 · What this look is not

| | |
|---|---|
| not `persa` | persa is desaturated, hazy, bloomed, vignetted and grained, and nothing in it reaches pure black or pure white. Zak's ground **is** pure black and its plate is saturated and clean. |
| not `motiongraphics` | no glow, no lit surfaces, no gradient stage, no violet. |
| not a film emulation | there is no measurable grain, no halation, no gate weave. Adding grain here is adding a texture the reference does not have. |
| not "cinematic" via a LUT | the look is the **framing** — black air, one window, no motion. A LUT will not produce it and cannot rescue a frame that lacks it. |
