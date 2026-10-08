# Porta från Remotion

Bas-prompt för att översätta en Remotion-komposition (React) till HyperFrames-HTML.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/remotion-to-hyperframes Port the composition at `src/HeroReveal.tsx` (Remotion project root: `.`) to HyperFrames. Keep the same duration, fps, and dimensions. Write `TRANSLATION_NOTES.md` for anything that doesn't translate cleanly.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/remotion-to-hyperframes` (installerad globalt i `~/.claude/skills/remotion-to-hyperframes/`)

> Källa: <https://hyperframes.heygen.com/prompting/remotion-migration> (avsnitt: Base prompt) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
