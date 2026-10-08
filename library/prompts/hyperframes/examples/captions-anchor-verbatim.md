# Textning: ren ordagrann (anchor)

Lägger lugna, ordagranna undertexter på en talking-head-video utan att röra bilden.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/embedded-captions Add captions to ./interview.mp4. Use the `anchor` identity — clean verbatim rail carrying the spoken words, readable lower-third. Promote the single hardest-hitting word to an embed behind the speaker; highlight one key word in each rail line. Keep the source aspect ratio. Footage stays untouched.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/embedded-captions` (installerad globalt i `~/.claude/skills/embedded-captions/`)

> Källa: <https://hyperframes.heygen.com/prompting/captions-and-talking-heads> (avsnitt: Your first win) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
