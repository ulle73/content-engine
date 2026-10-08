# Vertikal explainer med highlight-textning

30 s vertikal explainer där nyckelord markeras via caption-highlight-komponenten.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/faceless-explainer 30-second vertical explainer. Add [`caption-highlight`](https://hyperframes.heygen.com/catalog/components/caption-highlight) captions, TikTok-style — the visible line stays up, one word highlighted at a time.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/faceless-explainer` (installerad globalt i `~/.claude/skills/faceless-explainer/`)
- Registerblock: `npx hyperframes add caption-highlight`

> Källa: <https://hyperframes.heygen.com/prompting/captions-catalog> (avsnitt: Example prompts) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
