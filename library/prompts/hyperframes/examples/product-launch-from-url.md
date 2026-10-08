# Produktlansering från URL (45 s)

45 s lanseringsvideo från en produkt-URL: hook, tre funktionsbeats med UI-skärmdumpar, slutkort. TTS + musik.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/product-launch-video Make a 45-second 1920x1080 launch video for https://linear.app. Energetic but minimal, use the site's own palette and screenshots. Structure: hook stating the problem, 3 feature beats with UI captures and one-line captions, end card with logo + "Try it free". Female TTS voice, confident tone, subtle electronic BGM under -18dB. **Spectacle beat:** One exaggerated moment: the end card's logo lands with a bloom flash and a fast light-sweep across the wordmark. Feature beats stay restrained.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/product-launch-video` (installerad globalt i `~/.claude/skills/product-launch-video/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Product launch from a URL) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
