# Visuell spec: frostad kommandopalett

6 s: exakt specad glas-kommandopalett (mått, radie, rgba, timing).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
6-second 1920x1080. A frosted-glass command palette (640x84px, 20px radius, rgba(255,255,255,0.08) fill, 1px rgba(255,255,255,0.25) border, heavy backdrop blur) centered on a #0b0f1a field with two soft accent glows drifting slowly — #5b6cff upper-left, #22d3a5 lower-right, ~400px, 20% opacity. At 0.4s the palette scales in 0.96→1 settling with back.out(1.2). At 0.8s a grey placeholder "Search commands…" types on; at 2.2s it fades out over 0.2s and the query "render 4k" types in white. At 2.8s three result rows (56px tall, 12px gaps: icon square, label, shortcut chip) cascade in as a detached list below the fixed bar, staggered 0.12s, each rising 12px with back.out(1.4). At 4.2s a 10%-opacity #5b6cff fill sweeps left to right across the first row and its shortcut chip pulses once. Rows and glows keep a barely-visible drift to the end. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/visual-specs> (avsnitt: Two more worked specs) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
