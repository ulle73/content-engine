# Ordmärke med ambient polish

6 s: platina-ordmärke på nästan svart med anamorfisk flare, korn och glans.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 6-second 1920x1080 video. A wordmark logo — "HYPERFRAMES" in platinum on near-black — settles center-frame, then holds — but keep it alive with a film grain overlay and a slow 3% push-in, plus one shimmer sweep across the wordmark at 4s. Use the `grain-overlay`, `parallax-zoom`, and `shimmer-sweep` registry components. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add grain-overlay`, `npx hyperframes add parallax-zoom`, `npx hyperframes add shimmer-sweep`

> Källa: <https://hyperframes.heygen.com/prompting/vfx-and-liquid-glass> (avsnitt: Ambient polish) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
