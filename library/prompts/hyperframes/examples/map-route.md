# Kartrutt med glödande båge

8 s: mörk världskarta, en glödande båge SF→Tokyo, nål med chockvåg, kamerazoom och etikett som skrivs ut.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 8-second 1920x1080 video. Dark world map, a glowing arc animates from San Francisco to Tokyo over 3s, destination pin drops with a pulse, then camera zooms into Tokyo and the label "LATENCY: 89ms" types on. Use the `nyc-paris-flight` registry block as the base pattern, restyle to teal on charcoal. No narration. **Spectacle beat:** The destination pin's landing fires a triple concentric shockwave that expands past the label and fades, with a brief chromatic split on the pin.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add nyc-paris-flight`

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Map route) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
