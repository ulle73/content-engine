# Explainer från inklistrad text

~60 s vertikal explainer: en idé per scen, stor typografi, diagram, TTS och inbäddade captions.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/faceless-explainer Turn this into a ~60-second 1080x1920 vertical explainer: [paste your text]. One idea per scene, big typography, diagrams over stock footage, brand color #FF5533 on off-black. Male TTS voice, calm. Embedded captions, keywords highlighted in the brand color. **Spectacle beat:** One exaggerated moment: the final CTA's key phrase slams in at 1.5× with a chromatic split that resolves in 0.2s. Every other scene stays typographically calm.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/faceless-explainer` (installerad globalt i `~/.claude/skills/faceless-explainer/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Explainer from pasted text) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
