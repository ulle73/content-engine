# Personlig välkomstvideo

10 s välkomstklipp som hälsar varje ny kund vid förnamn och visar deras logga (batch-render).

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
A 10-second welcome clip that greets each new signup by first name and shows their company logo. I'll supply a list of `{ firstName, logoUrl }` records.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/variables-and-templating> (avsnitt: Personalization asks) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
