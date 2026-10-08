# Motion

Persa moves less than either sibling style. Getting the *restraint* right matters
more than getting any single move right — an over-animated persa edit stops being
persa immediately.

All timings measured at 30fps off the reference. Frames, not seconds.

---

## The measured cadence

| Move | Timing | What it is |
|---|---|---|
| **Word caption** | **0 frames** | It **hard-cuts**. See `captions.md` §1. |
| **Emphasis word in** | 5f (`--pa-dur-emph`) | scale 0.94→1 + opacity, glow blooms |
| **Slam headline** | 4f (`--pa-dur-slam`) | lands hard, no overshoot |
| **Panel in** | 9f (`--pa-dur-in`) | opacity + scale 0.97→1, `--pa-ease-in` |
| **Panel out** | 8f (`--pa-dur-out`) | **straight opacity fade in place** |
| **Plate drift** | continuous, 6s | scale 1.00→1.03, **linear**, never eased |

---

## Three standing rules

### 1 · The panel does not slide
Measured on `stills/11-panel-exit-30fps.png`: over 8 frames the panel simply fades
to nothing where it stands. It does not slide off, wipe, or scale away. The
wordmark on it holds a beat longer than the UI underneath — a small stagger that
is worth copying.

Entrances are the same in reverse. **No directional motion on panels.** If you
find yourself writing an x/y tween on a `.pa-panel`, that is a different style.

### 2 · Nothing is ever perfectly still
The plate carries a continuous slow push-in — `scale 1.00 → 1.03` over ~6s,
**linear**, never eased. This is the difference between a video and a slideshow,
and it is the one animation that runs under everything else.

`--pa-ease-drift` is `linear` on purpose. An eased drift reads as a camera move
and fights the cut.

### 3 · Enter slow, leave fast
Entrances 5–9 frames on `--pa-ease-in` (expo-out — it lands and settles).
Exits 8 frames or fewer. Elements are *gone*, not dissolved over a second.

---

## Transforms only

Animate `opacity, x, y, scale, scaleX/Y, rotation` plus `filter: blur()`.
Never `top/left/width/height` — it stutters and fails lint. Bars and rails grow
with `scaleX` + `transform-origin`.

`scripts/check-persa.sh` fails a segment that animates layout properties.

---

## Timing anchors

Every graphic enters **on, or a hair after, the tight-transcript word onset** it
illustrates — never before. Round-number timings are banned; if a value in your
composition is `2.0s` or `90f`, it was guessed, not derived.

Exit at the OUT word + ~0.3s. Cap a support panel at ~10s, then change it rather
than let it sit.

---

## Cuts

The reference cuts on the beat of the speech, hard, with no dissolves anywhere.
The only "transition" in the whole style is the panel fade above. There is no
whip pan, no zoom blur, no light leak, no glitch. If a cut needs help, the help is
a **sound**, not a transition — see `sound-design.md`.
