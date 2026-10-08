# Scrolla kod till en nyckelrad

6 s: scrollar en lång källfil och stannar på en markerad rad.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 6-second 1920x1080 video. Scroll a ~60-line source file so line 44 (`return dedupeFrames(frames)`) arrives at center and gets spotlighted; ease the scroll and let it settle without snapping. Use the `code-scroll` registry block. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add code-scroll`

> Källa: <https://hyperframes.heygen.com/prompting/code-blocks> (avsnitt: Prompting a scroll-through) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
