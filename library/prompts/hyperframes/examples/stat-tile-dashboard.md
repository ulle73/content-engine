# Dashboard med statistikbrickor

10 s: fyra brickor i 2x2 räknar upp med egna eases, sparklines ritas, alla blixtrar i takt.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
10-second 1920x1080 video, near-black background. Four stat tiles slide up in a 2x2 grid, staggered: "99.99% uptime", "42ms p50", "18M req/day", "0 incidents". Each tile's number counts or decrements to its value with its own easing; sparklines draw underneath in teal. At 8s the grid scales back and "Built to hold." fades in above. No audio. **Spectacle beat:** When the fourth tile lands, all four numerals flare in unison for three frames — one synchronized accent, then back to restrained idles.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Stat tile dashboard) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
