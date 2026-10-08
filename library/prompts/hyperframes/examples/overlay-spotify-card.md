# Transparent overlay (Spotify-kort)

Ren transparent overlay att lägga ovanpå egen film – exempel med spotify-card-blocket.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics Transparent overlay only — a [`spotify-card`](https://hyperframes.heygen.com/catalog/blocks/spotify-card) now-playing widget animating in, bottom-left. Export as transparent WebM so I can drop it over footage in my editor.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add spotify-card`

> Källa: <https://hyperframes.heygen.com/prompting/overlays-and-lower-thirds> (avsnitt: Example prompts) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
