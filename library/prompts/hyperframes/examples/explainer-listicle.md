# Listicle (5 saker)

~45 s vertikal listicle, en punkt per scen.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/faceless-explainer Make a ~45-second 1080x1920 listicle: "5 habits of fast-shipping teams". Listicle angle — one habit per scene, each with a big number and a one-line label, escalating energy toward #1. Off-black with a lime accent. Male TTS voice, upbeat. Embedded captions, the habit label highlighted each scene.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/faceless-explainer` (installerad globalt i `~/.claude/skills/faceless-explainer/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/explainers> (avsnitt: Listicle) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
