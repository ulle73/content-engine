# Visuell spec: nattlig titelkort

8 s titelkort där varje element namnges, placeras, färgsätts och tajmas – från lös beskrivning till exakt spec.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
8-second 1920x1080 title card. Scene, back to front: #0a0e2a night sky with faint grain; an orange radial glow (#ff6a2b core ~150px, falling off to transparent by ~430px) igniting at the mountain peak's right shoulder from 2s, positioned so its upper falloff reaches the wordmark's baseline; over it a huge concentric ring system (5 rings, 1px strokes at 8% white opacity, innermost ring glowing #4a5fd9) centered 40% from the top; a low-poly mountain (6-8 dark navy facets, #141a3d–#1e2650) filling the lower third with its apex left of center, a white road S-curving up its face with a soft glow; thin horizontal cloud streaks (white, 6% opacity) drifting right at two heights; a man's silhouette, pure black, ~90px tall, bottom-right, fading in at 2.5s. At 3.5s "SHOWREEL" — thin geometric sans, ~140px, 0.35em tracking, white at 90% — fades in per letter across the ring center, the glow bleeding up through the letterforms above the peak. Slow 4% push-in across the full 8s. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/visual-specs> (avsnitt: A loose description, then a spec) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
