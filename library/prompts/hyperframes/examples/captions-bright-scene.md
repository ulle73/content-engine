# Textning i ljus dagsljusscen

Ordagranna undertexter som förblir läsbara mot ljus bakgrund (utomhus-vlogg).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/embedded-captions Add verbatim captions to ./outdoor-vlog.mp4. It's a bright daylight scene, so use the `ink` identity — near-black type printed onto the surface — not a light-on-bright look that washes out. Keep it a readable rail. 16:9.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/embedded-captions` (installerad globalt i `~/.claude/skills/embedded-captions/`)

> Källa: <https://hyperframes.heygen.com/prompting/captions-and-talking-heads> (avsnitt: Bright-scene captions) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
