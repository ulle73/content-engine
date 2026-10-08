# Vertikal produktteaser 20 s

~20 s 9:16-teaser från en URL, supermininmal.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/product-launch-video Make a ~20-second 1080x1920 teaser for https://linear.app. Super minimal, just the hook. Beat 1 (0-4s): the problem in one line, big type. Beat 2 (4-16s): two feature beats, one UI capture each with a three-word caption. Beat 3 (16-20s): logo + "Try it free" end card, then settle into a gentle idle. Use the site's own palette. Female TTS voice, confident; no BGM.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/product-launch-video` (installerad globalt i `~/.claude/skills/product-launch-video/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/product-launch> (avsnitt: 20-second vertical teaser (9:16)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
