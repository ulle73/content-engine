# Hero som krossas/portal

8 s: en landningssida krossas eller dras in i en portal – VFX-ögonblick.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 8-second 1920x1080 video. Beat 1 (0-4s): a landing-page hero holds under directional light. Beat 2 (4-6s): the whole page shatters into glass fragments that scatter. Beat 3 (6-8s): bold white text slams in on black. Use the `vfx-shatter` registry block; the final beat reads "HTML IS VIDEO". No narration, no image or media files.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add vfx-shatter`

> Källa: <https://hyperframes.heygen.com/prompting/vfx-and-liquid-glass> (avsnitt: Shatter, portal, magnetic, and cursor moments) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
