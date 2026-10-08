# Hologramglob (Three.js, full spec)

1,8 s exakt specad Three.js-glob – exempel på hur man återskapar en referens med absoluta mål.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
1.8-second 1920x1080 video, Three.js via the adapter (seek-driven, no rAF). One continuous shot. Every element is still moving on the final frame.  **FIELD**  - blue-violet background, linear #2a24a8 → #12105e top-to-bottom, with a soft radial lift at center - faint blurred vertical cyan light-streaks (#5ee0e8 at ~10% opacity, ~340px spacing) drifting 70px left across the piece - deep corner vignette - soft-light film grain at ~6% (seeded noise)  **GLOBE**  - royal-blue sphere (#4348f2), lit from upper-left with a 0.58 ambient floor - a broad subtle satin band (#6470ff, very wide falloff, ~30% mix) sweeping the upper curve - a strong cyan rim-light line (#5ee8f0) tracing only the top edge - continents in TWO layers: - (a) a heavily-blurred darker-blue silhouette (#3439c2, 80% opacity) just under the surface, reading as a soft shadow shape - (b) a dot-matrix just above the surface on an equal-area grid (0.9° latitude rows, longitude step widening with latitude) - dot radius = 24–28% of row spacing — clear blue gaps between dots — growing slightly toward the equator, 85% dot opacity - two color populations: cyan-aqua #5ee0e8 north, spring-green #7ce97a from latitude ~32° southward, with seeded ±30% per-dot brightness variance - dots dimmed to 40% in the view-space lower-right shadow zone - continents read as distinct dotted landmasses covering ~30–35% of the visible hemisphere, with royal-blue ocean dominating the rest  **CAMERA**  - open EXTREMELY close: the sphere's curve fills the entire frame, horizon exiting the upper corners - then one continuous pull-back + crane (fov 52°→40°) - end with the dome filling the lower half edge-to-edge, its silhouette touching both frame edges, horizon at ~45% - ease power1.inOut computed over a 2.0s window while rendering 1.8s, so the move never settles on-screen - the globe rotates 28° about its vertical axis, linear, continents drifting right-to-left, never stopping  **ORBS** — 12 across three depth planes, world-anchored on the upper hemisphere so stems stay vertical  - popping at staggered starts 0.45s→1.15s (0.06–0.13s apart) - each rising 0.44–0.56s with back.out overshoot (vary 1.7–2.6 per orb), then bobbing ±8px on phase-offset sines forever - **5 midground** (~90–110px at end framing): soft mint body #a7ecc4, a darker-green under-shade #3f9b5e at lower-left, a pale rim #d6ffe8 top-right, no white core - each wrapped in a soft additive bloom sprite ~3.5x its diameter, whose texture is HOLLOW-centered, peaking ~35% just outside the orb edge. A bright-cored additive glow over the opaque orb blows the mint to lime. - plus a thin soft halo ring ~4.2x radius at 60% opacity, always subtler than the orb itself, with a slow 5% scale pulse - **4 background** — ~30px, sharp, tighter bloom - **3 foreground near-lens bokeh** — ~160–190px, dense mint radial-gradient sprites riding the camera at center-left / lower-center / upper-right, ~70% opacity, drifting ±30px laterally, no stems - **stems** — 2–3px additive cyan cylinders fading to transparent at the surface - tag canvas-generated sprite textures sRGB, or the mints wash out pale  **CAPTION** — "Across 82 Countries"  - Inter 300, 34px, 0.06em tracking, white at 90%, top-center 12% from the top - left-to-right per-letter fade starting t=1.0s, completing ~1.45s - then a slow 6px upward drift, still easing at the final frame  No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.
- Kräver ev. betald tjänst: api:bild/musikgenerering. Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/recreating-references> (avsnitt: Worked example: the hologram globe (full distilled spec)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
