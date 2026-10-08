# Kod som skrivs tecken för tecken

6 s: en mörk editor skriver ett kodexempel med syntaxfärg. För devtool-ads och tutorials.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 6-second 1920x1080 video. A dark editor types this snippet, character by character, caret tracking the frontier, then holds on the blinking cursor for the final second: ``` export async function render(comp: Composition) { await comp.seek(0); return comp.capture(); } ``` Use the `code-typing` registry block. No narration, no image or media files.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add code-typing`

> Källa: <https://hyperframes.heygen.com/prompting/code-blocks> (avsnitt: Prompting a typing reveal) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
