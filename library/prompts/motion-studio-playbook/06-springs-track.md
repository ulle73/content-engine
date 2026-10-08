# Fjädrar i sluten form + track() för värden med många mål

**Vad:** `springs.mjs` – egen implementation av dämpade fjädrar som ren funktion av tiden, plus
`track()` som låter ett värde byta mål många gånger (summa av en fjäder per ändring – exakt tack
vare superposition). Även seedat brus (`hash`, `noise1`, `boil`) och taktslagshjälp (`beatInfo`, `pulse`).
**När:** alla `seek(t)`-filmer (ren HTML/Canvas), och som referens för hur man ber Claude bygga
rörelse utan integratorer. Självtest: `node library/prompts/motion-studio-playbook/springs.selftest.mjs`.

## Användning

```js
import { track, trackObj, springFrom, hold, noise1, pulse } from "./springs.mjs";

// x byter mål tre gånger – varje byte startar en ny fjäder ovanpå den förra
const x = track(t, [{ t: 0, v: -300 }, { t: 0.4, v: 0 }, { t: 2.0, v: 240, spring: { freq: 3, zeta: 0.6 } }, { t: 3.1, v: 0 }]);

// hela rektangeln (morph): position, storlek och hörnradie i ett anrop
const box = trackObj(t, [
  { t: 0,   v: { x: 390, y: 900, w: 300, h: 90,  r: 45 } },   // knapp
  { t: 0.5, v: { x: 140, y: 880, w: 800, h: 120, r: 24 } },   // sökfält
  { t: 1.0, v: { x: 140, y: 600, w: 800, h: 700, r: 32 } },   // kort
]);

// diskret innehåll (vilken text/ikon som syns)
const label = hold(t, [{ t: 0, v: "Sök Golfkuponger" }, { t: 0.5, v: "" }, { t: 1.0, v: "Välj belopp" }]);

// drag: medan musen hålls följer värdet pekaren; vid släpp fjädrar det tillbaka från aktuell position och fart
const released = 2.4, x0 = 812, v0 = 900;
const knob = t < released ? cursorX(t) : springFrom(t - released, x0, v0, 640, { freq: 2.5, zeta: 0.55 });

// liv i linjer och på takten
const wobble = (noise1(t * 1.5, 42) - 0.5) * 4;
const bump = 1 + 0.06 * pulse(t, beats);
```

## Parametrar

| zeta | Känsla |
|---|---|
| 0.45–0.6 | Livlig, tydlig översväng (lekfullt, fräckt) |
| 0.7–0.85 | "En liten översväng som mest" – premium-UI |
| 1.0 | Kritiskt dämpad, ingen översväng (lugnt, seriöst) |
| > 1 | Trög, tung |

`freq` (Hz): 1.5 = mjuk och långsam, 2–3 = normalt UI, 4–6 = snärtigt. Insvängningstid ≈ 4 / (zeta · 2π · freq).

## Prompt-rad att klistra in

```text
Motion uses closed-form springs (no integrators, no state): import springFrom/track/trackObj/hold from
springs.mjs. A value that changes target several times is track(t, keys) – a sum of one spring per change.
Releases after a drag use springFrom(t - tRelease, x0, v0, target). Randomness only via hash/noise1.
```
