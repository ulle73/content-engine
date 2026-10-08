# Renderkontrakt – varje bildruta är en ren funktion av tiden

**Vad:** ett kontrakt att klistra in först i varje prompt där Claude bygger motion i ren HTML/Canvas
och renderar med Playwright/Chrome + ffmpeg. Det gör att filmen kan renderas parallellt, i vilken
ordning som helst, om och om igen – med exakt samma pixlar – och att en scen kan fixas utan att
resten ändras.

**När:** HTML/Canvas/WebGL-filmer som renderas bildruta för bildruta (egen pipeline,
`html-playwright`). I **HyperFrames** gäller ramverkets eget kontrakt (pausad tidslinje som seekas –
se skillen `hyperframes-core`) och i **Remotion** `useCurrentFrame()`; principerna nedan är desamma
och är bra att upprepa i prompten även där.

## Prompt (klistra in som första block)

```text
RENDER CONTRACT – follow exactly, it is how the film gets rendered.

1. The page exposes window.seek(t) (t in seconds, float). seek(t) sets EVERY visual property
   from t alone and returns a Promise that resolves when the frame is fully painted.
   Same t => same pixels, no matter which t was rendered before (frames are rendered in
   parallel workers and out of order).
2. Forbidden: CSS transitions/animations that run on their own, setTimeout/setInterval,
   requestAnimationFrame-driven state, Date.now()/performance.now(), Math.random(),
   any state carried from one frame to the next, video elements that play by themselves.
3. Randomness = seeded noise: hash(seed, i) -> [0,1). Hand-drawn "boil" = reseed at a fixed
   rate (e.g. floor(t*12)). Particles, jitter and grain are functions of (index, t).
4. Motion = closed-form math of t: easing curves, closed-form springs (no integrators),
   multi-target values as a sum of springs (track()). Camera is a function of t too.
5. Before frame 0: await document.fonts.ready, decode every image (img.decode()), load
   textures. seek() must never paint a half-loaded frame.
6. Motion blur (optional, for fast moves): the renderer captures N subframes per frame at
   t + k*(shutter/fps)/N (shutter 0.5 = 180°) and averages them. Never average across a
   hard cut – cuts are marked in window.CUTS = [t1, t2, ...] so the renderer can skip blur there.
7. Layout is fixed: width/height from window.FILM = {w, h, fps, duration}. Text never
   depends on viewport units that change between renders.
8. Audio is not played by the page. Sound is placed afterwards from a cue list
   (cues.json: [{sfx, t, gain}]) that is derived from the SAME timeline as the picture.

Before building the whole film: render frames at t = 0, 25%, 50%, 75% and the last frame,
show them, then render one time point twice in different order and confirm identical hashes.
```

## Minimal skelett (egen kod)

```html
<!doctype html>
<html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#082f27;overflow:hidden} #stage{position:relative;width:1080px;height:1920px}</style>
</head><body><div id="stage"></div>
<script type="module">
  import { track, springStep, noise1 } from "./springs.mjs";       // se 06-springs-track.md
  window.FILM = { w: 1080, h: 1920, fps: 30, duration: 15 };
  window.CUTS = [5.0, 10.0];
  const stage = document.getElementById("stage");
  const card = Object.assign(document.createElement("div"), { className: "card" });
  stage.append(card);
  const ready = Promise.all([document.fonts.ready]);

  function paint(t) {
    const x = track(t, [{ t: 0, v: -400 }, { t: 0.4, v: 0 }, { t: 4.6, v: 600 }]);
    const wobble = (noise1(t * 2, 7) - 0.5) * 6;                     // seedad, deterministisk
    card.style.transform = `translate(${x}px, ${wobble}px)`;
  }
  window.seek = async (t) => { await ready; paint(t); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); };
</script></body></html>
```

Renderaren (Playwright) gör per bildruta: `await page.evaluate(t => window.seek(t), t)` →
`page.screenshot()`; med motion blur N skärmdumpar per ruta som medelvärdesbildas (Pillow eller
`ffmpeg -vf tmix=frames=N`). Determinismkontroll och kontaktark: `review.py` (se
`09-critique-loop.md`).

## Vanliga fel att be Claude kontrollera

- Text som byts inne i en container som samtidigt ändrar storlek överlappar – ge texten egen in/ut-timing.
- `will-change` / GPU-lager på element som kameran skalar ger suddig text – undvik på skalade element.
- En loop "hackar" om sista rutan inte är identisk med första i både **position och hastighet** (även muspekare).
- Webbfonter som inte laddats före ruta 0 ger en ruta med reservfont – vänta på `document.fonts.ready`.
- Videoelement: seeka `video.currentTime = t - start` och vänta på `seeked`, spela aldrig upp.
