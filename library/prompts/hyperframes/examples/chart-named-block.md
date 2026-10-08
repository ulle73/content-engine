# Diagram via registerblock

12 s stapeldiagram byggt på ett namngivet registerblock (data-chart).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 12-second 1920x1080 video. Title "Most-used languages" with the subtitle "share of respondents, 2026 survey". Turn this into an animated bar chart with a staggered reveal and value labels counting up on each bar, each label suffixed `%`: ``` Python 41, TypeScript 33, Rust 19, Go 14, Java 9 ``` Use the `data-chart` registry block. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add data-chart`

> Källa: <https://hyperframes.heygen.com/prompting/data-and-maps> (avsnitt: Charts: name the block, or hand-draw) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
