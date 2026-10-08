# USA-karta (choropleth)

12 s: delstater färgas efter andel, med förklaring och värdeetiketter.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 12-second 1920x1080 video. A US choropleth shades states by adoption rate with staggered reveals and a gradient legend, then connection arcs draw between San Francisco, Austin, and New York. Use the `us-map` and `us-map-flow` registry blocks. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add us-map`, `npx hyperframes add us-map-flow`

> Källa: <https://hyperframes.heygen.com/prompting/data-and-maps> (avsnitt: Maps: match the ask to the map) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
