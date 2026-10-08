# 3D-kort i Three.js

9 s: tre rundade kort reser sig ett i taget i isometrisk vy med mjuka skuggor och specular-svep.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
9-second 1920x1080 video, light warm cream background. Build the scene in Three.js via the adapter: three rounded card meshes labeled "Design", "Build", "Ship" lie flat on the ground plane, camera at a fixed 3/4 isometric angle, soft directional light + ambient so the cards cast soft shadows. One at a time each card lifts and straightens upright to face the viewer center-frame while the other two slide apart and dim; then it returns. Finish with all three standing upright in a row by 8.5s, hold with a subtle ambient idle. All easing power3.inOut. No audio. **Spectacle beat:** As the cards rise into their stack, a single specular sweep rakes across all three faces in sequence, catching each edge.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: 3D cards (Three.js)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
