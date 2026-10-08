# Intervju som 16:9-datafilm

Klipper om ett analytikerintervju till en klinisk 16:9-explainer med datakort och sidopaneler.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/talking-head-recut Recut ./analyst-interview.mp4 as a 16:9 explainer with a clinical style. Split layout: speaker on the right, data cards on the left. Cards for each claim — a count-up for the headline number, a swiss-grid comparison for the two options, a terminal-style callout for the technical bit. Auto-pace the card count for a 5-minute clip. Footage untouched.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/talking-head-recut` (installerad globalt i `~/.claude/skills/talking-head-recut/`)

> Källa: <https://hyperframes.heygen.com/prompting/captions-and-talking-heads> (avsnitt: Landscape data recut) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
