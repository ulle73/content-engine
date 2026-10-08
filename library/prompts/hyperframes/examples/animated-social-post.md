# Animerat socialt inlägg (tweet-kort)

7 s 4:5: ett tweet-kort glider upp över mjuk gradient, likes räknar upp, 3D-tilt och highlight-svep.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 7-second 1080x1350 vertical video. A real tweet card (handle @hyperframes, text "we render video from HTML now. no timeline UI. just code.") slides up over a soft animated gradient, likes counter ticks 0→1.2K, then the card tilts in 3D and a highlight sweeps the second sentence. Hold on the card at the end with a subtle ambient idle (slow breathing scale). Use the `x-post` and `vfx-liquid-background` registry blocks. No narration, no image or media files. **Spectacle beat:** When the like count lands, the heart pops to 1.6× with a radial burst of ~24 seeded particles and settles — one moment, nothing else exaggerated.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add x-post`, `npx hyperframes add vfx-liquid-background`

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Animated social post) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
