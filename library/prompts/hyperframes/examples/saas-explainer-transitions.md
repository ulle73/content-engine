# SaaS-explainer med namngivna övergångar

Sexscenig explainer där varje skarv får en namngiven övergång (whip-pan m.fl.).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/general-video Six-scene SaaS explainer. Use [`whip-pan`](https://hyperframes.heygen.com/catalog/blocks/whip-pan) as the primary transition between related points, and one [`cinematic-zoom`](https://hyperframes.heygen.com/catalog/blocks/cinematic-zoom) into the final pricing reveal. Medium energy, ~0.4s each.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/general-video` (installerad globalt i `~/.claude/skills/general-video/`)
- Registerblock: `npx hyperframes add whip-pan`, `npx hyperframes add cinematic-zoom`

> Källa: <https://hyperframes.heygen.com/prompting/transitions> (avsnitt: Example prompts) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
