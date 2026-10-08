# Visuell spec: ordet PRECISION

7 s: ordmärke på off-black med fint filmkorn – exakt specad typografi och rörelse.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
7-second 1920x1080. Off-black #101014 field with fine static film grain at 4%. The word "PRECISION" in ~220px heavy condensed caps (a heavy system face condensed with scaleX 0.82), white, 0.02em tracking, centered: its letters assemble from alternating top/bottom 40px offsets with power3.out and a 0.05s stagger, starting 0.3s. At 1.8s a 2px hairline rule draws left-to-right beneath the word, 60% of its width, centered. At 2.4s a 40px tabular-mono counter fades in below and ticks 99.999 → 00.001 mm over 2.2s with expo.out deceleration. At 5.2s the whole lockup eases to 1.03 scale over 0.5s while the word cools from white to #d8d8de, then settles into a slow ±1% breathing idle to the end. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/visual-specs> (avsnitt: Two more worked specs) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
