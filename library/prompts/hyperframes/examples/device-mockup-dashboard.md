# Dashboard i enhetsmockup

15 s: egen dashboard-UI på skärmen av en riktig enhet (iPhone/MacBook).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/product-launch-video 15-second 1920x1080 video. Our dashboard UI lives on the screen of a real iPhone 15 Pro Max that turntables slowly under product-review lighting, then a MacBook Pro slides in beside it showing the same UI wider. Use the `vfx-iphone-device` registry block. No narration.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/product-launch-video` (installerad globalt i `~/.claude/skills/product-launch-video/`)
- Registerblock: `npx hyperframes add vfx-iphone-device`

> Källa: <https://hyperframes.heygen.com/prompting/vfx-and-liquid-glass> (avsnitt: Device mockups) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
