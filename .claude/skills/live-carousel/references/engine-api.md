# Slide anatomy and the `LC` engine

## A slide file (`src/<name>.html`)

`build.py` turns each source file into `slides/<name>/index.html`, a standalone HyperFrames
composition. The skeleton (copy it from any template slide):

```html
<head>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    /*@CHROME@*/            /* ← fonts.css + chrome.css (motion) or photo.css (photo) */
    /* slide-specific CSS */
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="8" data-width="1080" data-height="1350">
    <div id="scene" class="scene clip" data-start="0" data-duration="8" data-track-index="0">
      <div id="world" class="world">
        <canvas id="grid" class="grid" width="1080" height="1350"></canvas>
        <div id="glow" class="glow"></div>
        <div class="topbar">…</div><div class="hairline"></div>
        <div id="small-top" class="small">…</div>
        <div id="wordbox" class="wordbox"><div id="w" class="big" data-word="WEIGHT."></div></div>
        <div id="small-bot" class="small">…</div>
        <div id="fx" class="layer"></div>
        <div id="balls" class="layer"></div>
        <div id="ruler" class="ruler"></div>
      </div>
      <!--@GRAIN@-->
    </div>
    <audio id="mix" src="assets/audio/mix.wav" data-start="0" data-duration="8" data-track-index="2" data-volume="1"></audio>
  </div>
  <script>//@ENGINE@</script>
  <script>
    (function () {
      const L = window.LC, DUR = 8;
      function build() {
        /* measure text, create elements, precompute paths: once */
        function render(t) { /* set every animated style from t alone */ }
        L.run(DUR, render);      // registers window.__timelines["main"] as a paused GSAP clock
      }
      document.fonts.load("900 100px Anybody");
      document.fonts.load("500 26px 'JetBrains Mono'");
      document.fonts.load("italic 420 76px Fraunces");
      document.fonts.ready.then(build);
    })();
  </script>
</body>
```

Contract details that matter:
- `#root` must carry `data-composition-id="main"`, `data-duration` = DUR, and the 1080x1350 size.
  The `.clip` scene and the `<audio>` repeat the same duration.
- The renderer drives `window.__timelines["main"]`. Do all animation in `render(t)`, called from
  that one paused timeline (`L.run` sets it up). Don't use CSS animations or autoplaying tweens.
  The film grain is the one exception, because HyperFrames seeks CSS keyframes.
- The audio element plays `assets/audio/mix.wav`. `build.py` copies `audio/out/<name>.wav` there, or
  silence if it doesn't exist yet.
- Layout markers: put `data-layout-allow-overlap` / `data-layout-allow-occlusion` on elements that
  overlap on purpose (word swaps, balls over text), so `check` doesn't flag them.
  `data-layout-allow-overflow` is for elements that go off-canvas on purpose.

## `LC`: time helpers

| function | what it does |
| --- | --- |
| `clamp(v,a=0,b=1)`, `lerp(a,b,s)`, `prog(t,t0,t1)` | basics; `prog` gives 0..1 progress of t through [t0,t1] |
| `easeIn/easeOut/easeInOut/easeOutQuint(s)`, `easeOutBack(s,k)` | easing on 0..1 |
| `kick(dt, freq=3, damp=7)` | damped spring impulse: 0 at dt=0, kicks, rings out (shakes, wobbles) |
| `settle(dt, freq=2.2, damp=6)` | spring 0→1 with overshoot (pop-ins); 0 for dt ≤ 0 |
| `pulse(t, c, w)` | gaussian bump centred at c |
| `hash(n)` | deterministic pseudo-random 0..1, used in place of Math.random |

## `LC`: the protagonist (ball physics)

```js
const path = L.makePath([
  { t: 0,   x: -70, y: 800 },                                   // enters from off-canvas left
  { t: 1.0, x: 300, y: 560, h: 430, contact: { q: 0.62 } },      // parabola (apex h px above the chord) landing with squash q
  { t: 2.0, x: 520, y: 560, h: 380, contact: { q: 0.55 } },
  { t: 3.0, x: 1290, y: 120, h: 260, ease: "inOut" },           // exits right (x eases: linear|in|out|inOut)
]);
const ball = L.makeBall(document.getElementById("balls"), "", 44);   // radius 44
// in render(t):
const s = L.ballState(path, t, 44);  // {x,y,vx,vy,st(stretch),q(squash),ang}
L.applyBall(ball, s);                // stretch along velocity, squash at contacts (volume kept)
```
Ghost trails: `L.makeBall(parent, "ghost", R)`, rendered at `t - k*0.05` with opacity tied to speed.
The CSS for `.ball-pos/.ball-squash/.ball-stretch` is in `chrome.css`. To change what the
protagonist looks like, restyle `.ball-stretch` (the template uses an orange gradient disc) or put
your own SVG inside it.

## `LC`: type

```js
const chars = L.buildWord(el);                 // el has data-word="WEIGHT."; returns [{el, c, base}]
const fit = L.fitWord(el, chars, 936, 330, 52); // fill 936 px: font-size ≤ 330, wdth ≥ 52 → {F, w}
const m = L.measureWord(chars, fit.F, root);    // per glyph: {cx, top, base, w, left} in root px
// animate per glyph: c.el.style.setProperty("--w", w0 * 1.3)  → width axis (squash wider)
//                    c.el.style.transform = `translateY(..) scaleY(..)` (origin is the baseline)
```

## `LC`: scenery and effects

- `makeGrid(canvas, {color, gap})` returns `grid(t, waves, alive)`. A dot grid. `waves = [{t, x, y, a, v}]`
  sends shockwave ripples, and `alive` (0..1) makes it breathe.
- `makeBurst(parent, n, seed, cls)` returns `burst(t, t0, x, y, life)`. Deterministic diamond/dot
  confetti with gravity.
- `makeRuler(root, {frameStart, frames, width, duration, keys})` returns `ruler(t)`. A timeline
  ruler whose frame labels continue across slides. `keys` are the times that pop keyframe diamonds.
- `rel(el, root)` gives an element's box relative to root (build time only).
- `run(DUR, render)` creates the paused GSAP clock and registers it.

## Common moves

- Screen shake: `world.style.transform = translate(${L.kick(t-hit, 9, 9)*12}px, …)`.
- An impact frame: 2 frames of an inverted flash layer (`mix-blend-mode: difference`) on the slam.
- Word flip: per-glyph `rotateX` from 0 to 90° on the old word, then from -90° to 0 on the new one,
  staggered 0.03 s per glyph. The wordbox has a `perspective`.
- Typing: `textContent = word.slice(0, Math.floor(L.prog(t, t0, t1) * word.length))`, plus a caret
  that blinks on 0.25 s steps.
- Draw-on lines: SVG path with `strokeDasharray = len`, and `strokeDashoffset = len * (1 - p)`.
