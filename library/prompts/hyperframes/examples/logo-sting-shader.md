# Logo sting med shader-övergång

5 s: ordmärket byggs av ~1200 partiklar, swirl-vortex-shader, lockup med tagline på vitt.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 5-second 1920x1080 logo sting. Beat 1 (0-2s): the word "ACME" assembles from scattered particles. Beat 2 (2-3s): full-frame `swirl-vortex` shader transition. Beat 3 (3-5s): logo lockup + tagline "Ship faster." settles on white and holds with a subtle ambient idle. Use `code-particle-assemble` for the assembly. **Spectacle beat:** The particle assembly IS the spectacle — ~1200 seeded particles converging with visible motion trails, and a single bloom flash on the frame the wordmark completes.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add swirl-vortex`, `npx hyperframes add code-particle-assemble`

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Logo sting with shader transition) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
