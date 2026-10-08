# Före/efter-delning

8 s: rörigt 'FÖRE'-UI mot rent 'EFTER'-kort, en skanningslinje sveper och städar bilden.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
8-second 1920x1080 video. Vertical split: left half labeled "BEFORE" shows a cluttered mock UI (grey, 12 overlapping windows drawn in CSS), right half "AFTER" shows one clean card. Both halves settle within the first second. A vertical divider line sweeps left to right at 4s, wiping the clutter into the clean state across the full frame. End on "One tool." centered. No audio. **Spectacle beat:** The divider's wipe is the moment — a bright scan-line travels the split with a bloom as it crosses, and the AFTER half resolves behind it.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Before / after split) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
