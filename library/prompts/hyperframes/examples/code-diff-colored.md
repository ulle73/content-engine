# Kod-diff i färg

6 s: en ändring i en fil visas som färgad diff, rader in/ut animeras.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 6-second 1920x1080 video. Show this edit to `api.ts` as a colored diff — the removed line collapses in red, the added line expands in green: removed: `const res = await fetch(url)` added: `const res = await fetch(url, { signal })` Use the `code-diff` registry block. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add code-diff`

> Källa: <https://hyperframes.heygen.com/prompting/code-blocks> (avsnitt: Prompting a diff or a highlight) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
