# Flygrutt på karta

6 s: realistisk karta där ett plan flyger mellan två städer (nyc-paris-flight).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 6-second 1920x1080 video. A realistic map with a plane flying between two cities, a marker circle at the origin, and a landing pop at the destination. Use the `nyc-paris-flight` registry block as base — the route runs New York (JFK) → Paris (CDG), labelled at both ends. Keep the block's own title card and route ticks. End on the settled map, not on the block's white-out hand-off frame. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add nyc-paris-flight`

> Källa: <https://hyperframes.heygen.com/prompting/data-and-maps> (avsnitt: Routes and flights) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
