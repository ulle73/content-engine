# Levande telemetripanel (inget står still)

6 s: en live-panel där varje element fortsätter röra sig efter entrén – demonstrerar regel 1 i Motion that reads premium.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
6-second 1920x1080 live telemetry panel: an `ARR · LIVE` eyebrow with a status dot, `PROD · US-EAST-1` opposite, `$4.200M` at display scale with a delta chip, a sparkline of the reading history beneath, and a footer row reading `LAST SYNC` and `READINGS`. The panel rises in and lands by 1.9s, then holds motionless to the end — the dot stops, the figure freezes, the sparkline stops extending, the footer stops updating.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/motion> (avsnitt: Rule 1 — Nothing ever fully stops) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
