# Sajtvisning (site tour)

30 s rundtur av en webbplats byggd av sajtens egna bilder.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/product-launch-video Make a 30-second 1920x1080 tour of https://example.com built from its own screenshots. Calm, editorial pace — show the homepage, two inner pages, and the footer. Full narration, warm male voice. This is a showcase, not a sales pitch.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/product-launch-video` (installerad globalt i `~/.claude/skills/product-launch-video/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/product-launch> (avsnitt: Site tour instead (same workflow, tour brief)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
