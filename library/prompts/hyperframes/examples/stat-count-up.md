# Siffra som räknar upp (ARR)

6 s: en jättesiffra rullar upp till $4.2M, '+312% YoY' stämplas in, sedelregn som spektakelbeat. Bygger på apple-money-count.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 6-second 1920x1080 video, dark navy background. Beat 1 (0-1s): label "ARR" fades up small, top-center. Beat 2 (1-4s): a giant number counts up to $4.2M with an odometer roll, easing out as it lands. Beat 3 (4-6s): "+312% YoY" stamps in below in green, then settles into a gentle ambient idle. Use the `apple-money-count` registry block as base. No narration.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)
- Registerblock: `npx hyperframes add apple-money-count`

> Källa: <https://hyperframes.heygen.com/prompting/data-and-maps> (avsnitt: Count-up stats) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
