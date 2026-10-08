# The PERSA grade

The look is not a filter you switch on. It is a specific, measurable place in
colour space, and the two reference reels sit in it from end to end. Everything
below was measured off those reels — the method is at the bottom so you can
re-run it.

---

## 1 · The look in one sentence

**Blue is pulled down hard everywhere; green is lifted in the shadows and the
highlights; the whole thing is desaturated, bloomed, vignetted and grained, and
nothing reaches pure black or pure white.**

That is it. Every other description of this look ("warm", "filmic", "vintage",
"Fuji") is downstream of those four moves.

---

## 2 · The measured numbers

Readings are means over 38–60 sampled frames per reel, split by luma band.
`G-R` and `B-R` are the channel differences that define the cast.

| Reading | Reel A | Reel B | What it means |
|---|---|---|---|
| Black point (1st pct) | 6 / 9 / 5 | 0 / 0 / 0 | A's floor is **lifted and green** |
| White point (99th pct) | 207 / 191 / 168 | 243 / 227 / 224 | ceiling is **warm and rolled off** |
| Shadows `G-R` / `B-R` | +0.6 / −3.9 | +2.5 / +0.9 | **green lift** in the shadows |
| Mids `G-R` / `B-R` | −3.4 / −28.3 | +3.9 / −17.7 | **blue crushed**, red leads on skin |
| Highlights `G-R` / `B-R` | +4.8 / −24.9 | +5.1 / −17.3 | **green + warm** in the bloom |
| Mean saturation | 0.294 | 0.216 | **desaturated** — nowhere near 0.5 |
| Vignette (corner ÷ centre luma) | 0.57 | — | corners at **57%** of centre |
| Grain (temporal σ, static wall) | 8.3 levels | — | real, visible grain — not codec noise |

### The single most important row
`B-R` in the mids: **−18 to −28**. If your render is at −5, it is not this look,
no matter how warm it feels. That one number does more work than the rest combined.

---

## 3 · ⭐ Two densities, one look

**The two reels disagree, and the disagreement is the useful part.** They are the
same grade at two densities:

- **Reel A — "haze."** Floor lifted to 6/9/5, ceiling pulled down to 207, blue
  crushed to −28, saturation 0.29. Milkier, softer, more diffusion. Reads warmer
  and older.
- **Reel B — "clean."** Floor at true 0, ceiling up at 243, blue at −18,
  saturation 0.22. More contrast, more punch, still unmistakably the same look.

`persa-grade.sh` ships the **midpoint** of the two, and `grade-check.py` tolerances
are wide enough to admit both. Pick a density per video and hold it for the whole
runtime — drifting between them across chapters is the one way this reads as sloppy.

To bias toward one, move the endpoint anchors only:
- toward **haze** — raise the `0/` anchors (`r 0.024 g 0.035 b 0.020`), lower the
  `1/` anchors (`r 0.812 g 0.749 b 0.659`).
- toward **clean** — drop the `0/` anchors to `0`, raise the `1/` anchors toward `1`.

Never chase a density by changing the mid anchors. Those carry the cast.

---

## 4 · The chain

```bash
bash scripts/persa-grade.sh assets/recording.mp4 assets/recording-graded.mp4 full
```

```
curves  r='0/0.012 0.25/0.200 0.5/0.440 0.75/0.643 1/0.882'
        g='0/0.020 0.25/0.206 0.5/0.440 0.75/0.663 1/0.820'
        b='0/0.012 0.25/0.194 0.5/0.349 0.75/0.561 1/0.769'
eq      saturation=0.88
bloom   split -> gblur sigma=26 -> curves 0/0 0.55/0.10 1/0.80 -> screen @ 0.22
vignette angle=PI/4.6
noise   alls=7:allf=t+u
```

Verified on a neutral grey ramp — the transfer lands on every measured anchor:

| Input | Out R/G/B | `G-R` | `B-R` | Target |
|---|---|---|---|---|
| 0 | 3 / 5 / 3 | +2 | 0 | black 3/5/3 |
| 32 | 24 / 26 / 26 | +2 | +2 | shadows +1.6 / −1.5 |
| 128 | 112 / 112 / 88 | 0 | −24 | mids +0.3 / −23 |
| 192 | 163 / 169 / 143 | +6 | −20 | highs +5.0 / −21 |
| 255 | 224 / 209 / 196 | −15 | −28 | white 225/209/196 |

### ⚠ Grade the plate, then bloom the comp
Use `plate` strength on footage that is going into a composition, and apply
bloom/vignette/grain **once, over the finished render**. Grading footage at `full`
and then laying ungraded graphics on top is the most common way this look fails —
the graphics sit *on* the image instead of *in* it, and it reads instantly.

```bash
bash scripts/persa-grade.sh assets/recording.mp4 assets/plate.mp4 plate   # before
# ... author, render segments, concat ...
bash scripts/persa-grade.sh out/visual.mp4 out/visual-look.mp4 soft       # after
```

### ⚠ The chain assumes reasonably neutral source footage
It is a **look**, not a corrector. One curve pass cannot pull a heavily-lit plate
into this space — tested on reel C, whose red practical light leaves it 4 readings
out of tolerance even after grading, because the source highlights are already
`B-R −145`.

If `grade-check.py` still fails after grading, the fix is upstream, not in the
curves. **`scripts/persa-balance.py` does it for you** — it measures the source's
own cast per luma band and writes the curve that cancels it:

```bash
python scripts/persa-balance.py assets/recording.mp4 --out assets/bal.mp4
bash   scripts/persa-grade.sh   assets/bal.mp4 assets/plate.mp4 plate
python scripts/grade-check.py   assets/plate.mp4
```

Verified on a real 16:9 talking head with a cool shadow fill and already-warm
highlights: **4 readings out of tolerance grading directly, a clean pass after
balancing**, with no hand-tuning of the persa curve.

Symptoms, if you would rather do it by hand:

| Reading | Means | Do this first |
|---|---|---|
| highlights `B-R` well past −40 | a coloured light source is blowing out | white-balance the plate |
| mids `G-R` past −12 | a strong magenta/red cast in the room | correct the cast, then grade |
| saturation > 0.40 | the source is far more saturated than the look | desaturate toward 0.3 before the chain |

Shoot-side, the look wants **soft, fairly neutral light with one warm practical**.
That is what both reference reels have, and it is why one curve pass is enough.

---

## 5 · Verifying

```bash
python scripts/grade-check.py out/final.mp4
```

Gates on the channel relationships and saturation; reports black/white points as
information only, because those swing with whatever is in the shot (reel A read a
207 ceiling and reel B 252 on the *same* grade — a blown window is not a grade error).

Calibration: it passes on both reference reels and fails on a third reel by a
different creator with 6 readings out of tolerance.

---

## 6 · How the numbers were taken

```bash
ffmpeg -i reel.mp4 -vf "fps=1,scale=540:-1" f/%03d.jpg      # sample frames
# then, per luma band (0-60 / 60-140 / 140-200), the per-channel mean;
# black/white points as the 1st/99th percentile; saturation as (max-min)/max.
```
Grain was measured as the **temporal** standard deviation of a static wall patch
across 15 consecutive frames — spatial σ alone cannot separate grain from texture.
Vignette as mean corner luma ÷ mean centre luma over all sampled frames.
