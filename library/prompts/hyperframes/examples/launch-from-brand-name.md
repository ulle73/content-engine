# Lansering från bara varumärkesnamn

~45 s – agenten hittar själv officiella sajten och bygger lanseringsvideon.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/product-launch-video Make a ~45-second 1920x1080 launch video for Linear. Find the official site, capture it, and use its own palette and screenshots. Angle: speed as the whole pitch. End card with logo + "Try it free". Confident female TTS voice, subtle electronic BGM under -18dB.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/product-launch-video` (installerad globalt i `~/.claude/skills/product-launch-video/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/product-launch> (avsnitt: Brand name only (agent finds the URL)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
