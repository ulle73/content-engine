# PR → buggfix-förklaring

~40 s video för utvecklare: symptom, orsak, fix – byggd från PR:ens diff.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/pr-to-video Make a ~40-second 1920x1080 fix-explainer from [PR URL], for developers. Fix angle: state the bug's symptom first, then the root cause, then the one-line fix on the `code-diff` block. End on version + repo URL. No narration, kinetic captions.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/pr-to-video` (installerad globalt i `~/.claude/skills/pr-to-video/`)
- Registerblock: `npx hyperframes add code-diff`

> Källa: <https://hyperframes.heygen.com/prompting/code-and-prs> (avsnitt: Fix explainer) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
