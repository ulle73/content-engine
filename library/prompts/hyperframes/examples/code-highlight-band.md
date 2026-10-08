# Kod med svepande highlight-band

5 s: en konfigfil där ett highlight-band sveper till raden som spelar roll.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 5-second 1920x1080 video. Show a 12-line config file; a highlight band sweeps to line 7 (`timeout: 30_000`) while the surrounding lines dim. Hold with line 7 lit and the cursor blinking. Use the `code-highlight` registry block. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add code-highlight`

> Källa: <https://hyperframes.heygen.com/prompting/code-blocks> (avsnitt: Prompting a diff or a highlight) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
