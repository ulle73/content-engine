# Motion grammar

## 1 · There is almost none, and that is the style — MEASURED

Over the full 39.9 seconds of the reference:

| | Measured |
|---|---|
| Window position / scale | **0px, 0%** — identical on all 240 sampled frames |
| Camera drift | **0px** — a static background edge correlated at zero shift throughout |
| Push-in / Ken Burns | **none** — the bright-span width held at 95px across the file |
| Title line | **static** — 80 frames diffed at max Δ 1.8/255 |
| Caption change | **0 frames of transition**, 53 times |
| Anything else | there is nothing else |

The subject moving inside the window is the only motion in the frame.

**This is the opposite of `motiongraphics`, and carrying that skill's habits
over is the fastest way to get zak wrong.** No drift, no continuous push, no
parallax, no floating, no breathing scale. The camera is bolted down.
`check-zak.sh` fails a tween on `.zk-plate` or a transform on `.zk-window`.

## 2 · The cut is the transition

Because nothing eases, the cut carries every change: caption to caption, scene
to scene, chapter to chapter. Zero frames, every time.

**If a cut needs help, the help is a sound** — never a fade, a dip to black, a
wipe, a blur, a whip, a zoom or a light leak. See `sound-design.md`.

## 3 · The one move

| Move | Frames @30fps | Ease |
|---|---|---|
| Window → full bleed | **6** | `--zk-ease-bleed` (expo-out) |

`.zk-window--bleed`. Once or twice in a whole video, on the single hardest line
in it. It works because it is the only thing that moves; a third use makes the
other two ordinary.

## 4 · Everything else is a hard cut

| | |
|---|---|
| Caption change | 0f |
| Window contents change | 0f |
| Scene change | 0f |
| Title line change | 0f, and only at a chapter boundary |
| Chapter card in/out | 0f |

## 5 · Animate transforms only

House rule, and it holds here: `opacity, x, y, scale, scaleX/Y, rotation` plus
`filter: blur()`. Never `top/left/width/height` for motion.

⚠ GSAP `fromTo` defaults to `immediateRender:true`, which applies a later
beat's `from` state at creation time and hides the element at frame 0. **Always
pass `immediateRender:false`.** It bites in every style in this studio and it
is worse here, where a single 6-frame tween is the only animation in the piece
and a failure is total.
