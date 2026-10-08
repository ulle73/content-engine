# Ämnes-explainer 30 s (16:9)

~30 s liggande explainer om ett tekniskt ämne (exempel: HTTPS) med diagram.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/faceless-explainer Make a ~30-second 1920x1080 explainer on how HTTPS keeps a request private, for a non-technical audience — the takeaway: your data is sealed before it leaves the browser. Concept angle: one idea per scene, big geometric type, a simple lock-and-key diagram as the centerpiece (swap the metaphor with the topic). Near-black ink on off-white with a deep-blue accent. Female TTS voice, warm and clear. Embedded captions, key terms highlighted in the accent color.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/faceless-explainer` (installerad globalt i `~/.claude/skills/faceless-explainer/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/explainers> (avsnitt: 30-second landscape topic explainer (16:9)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
