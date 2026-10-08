# PR → feature-reveal (30 s)

Gör en GitHub-PR till en 30 s video som leder med användarnyttan och visar diffen i ett beat.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/pr-to-video Make a 30-second 1920x1080 feature-reveal video from [PR URL]. Lead with what users get, not the diff; show the key code change with the `code-diff` block for one beat only; end on version number + repo URL. No narration, kinetic captions instead.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/pr-to-video` (installerad globalt i `~/.claude/skills/pr-to-video/`)
- Registerblock: `npx hyperframes add code-diff`

> Källa: <https://hyperframes.heygen.com/prompting/code-and-prs> (avsnitt: Your first win) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
