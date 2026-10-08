# How-to med diagram

~60 s liggande how-to för utvecklare, steg som diagram.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/faceless-explainer Make a ~60-second 1920x1080 how-to on setting up a CI pipeline, for developers. How-to angle: one step per scene, each built around a simple node-and-arrow diagram that draws on as the narration explains it. Charcoal with a teal accent. Calm male TTS voice. Embedded captions, the step name highlighted.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/faceless-explainer` (installerad globalt i `~/.claude/skills/faceless-explainer/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/explainers> (avsnitt: How-to with diagrams) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
