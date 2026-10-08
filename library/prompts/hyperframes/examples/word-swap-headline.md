# Ordbyte i rubrik (split-flap)

8 s: 'Make it ___.' där ordet byts som en split-flap-tavla; sista ordet landar i orange.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
8-second 1920x1080 video, white background. Static sentence "Make it ___." in huge black type stays centered while the blank cycles through "faster", "simpler", "yours" — each swap flips vertically like a split-flap board, 1.5s apart, with a slight blur on motion. Final word "yours." lands in orange and the period pops. No audio. **Spectacle beat:** The last swap lands hardest — that word arrives 1.3× behind a motion-blur streak that resolves as it settles.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Word-swap headline) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
