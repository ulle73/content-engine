# PR → refaktor-genomgång

~70 s genomgång av en refaktorering: före/efter-struktur, varför den blev bättre.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/pr-to-video Make a ~70-second 1920x1080 refactor-walkthrough from [PR URL], for developers. Refactor angle: why the old shape hurt, then the new shape, showing the before/after with the `code-morph` block for the key file. End on version + repo URL. Calm male TTS narration.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/pr-to-video` (installerad globalt i `~/.claude/skills/pr-to-video/`)
- Registerblock: `npx hyperframes add code-morph`
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/code-and-prs> (avsnitt: Refactor walkthrough) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
