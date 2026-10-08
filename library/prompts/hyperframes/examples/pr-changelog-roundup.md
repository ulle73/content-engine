# PR → changelog-sammanfattning

~40 s changelog-video från en PR: öppnar med versionen, listar ändringarna.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/pr-to-video Make a ~40-second 1920x1080 changelog video from [PR URL]. Changelog angle: open with the release line, then one beat per notable change — a short label and a one-line "what it does" each. Show at most two `code-diff` hunks across the whole video. End on version + repo URL. Calm male TTS narration, no captions.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/pr-to-video` (installerad globalt i `~/.claude/skills/pr-to-video/`)
- Registerblock: `npx hyperframes add code-diff`
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/code-and-prs> (avsnitt: Changelog roundup) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
