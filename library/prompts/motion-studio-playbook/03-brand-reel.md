# Varumärkes-/produktreel från en URL

**Vad:** mall för en kort produktfilm byggd på **riktigt material** från en webbplats: hook på max
fem ord, produkten sätts ihop, tre funktioner med muspekare, ett bevistal, logga + CTA, musik på takt.
**När:** lanseringar, kampanjer, säsongsstart – Golfkuponger.se, appen, förmånsportalsflödet.

## Prompt

```text
Build a [15]-second product reel for [Golfkuponger] from [https://golfkuponger.se].

INPUTS (ask me for anything missing, max 3 questions):
- Real assets only: fetch the logo (SVG if possible), colours, fonts and real screenshots/screen
  recordings from the URL or from the folder I give you. Never redraw UI, receipts or the app with AI.
- Facts only from the fact bank (skills/golfkuponger-friskvard / AdBrief.facts). One proof number,
  e.g. [300+ klubbar] – only if verified, otherwise use a non-numeric proof.
- Music: [my track / generated bed]. Beat grid from 07-beat-grid.md.

STRUCTURE (9:16 first, 1080x1920, 30 fps):
1. Hook, 0–1.5 s: max 5 words, on screen from frame 0. [Ditt friskvårdsbidrag = golf.]
2. Assemble, 1.5–4 s: the product builds itself from pieces (coupon card, app screen, club pins)
   that fly in and lock together on beats.
3. Three features, 4–11 s: one per ~2.3 s, each driven by a cursor doing a real action
   (click "Sök Golfkuponger", drag the amount slider, tap the code into the app).
4. Proof, 11–13 s: one number or one real quote, big and calm.
5. Logo + CTA, 13–15 s: real logo, one line CTA [Sök Golfkuponger i din förmånsportal].
Every cut lands on a beat; the drop (if any) hits the assemble moment or the logo.

BUILD: follow the render contract. Text sits inside the safe zone (middle ~70% of height).
Then recompose – don't crop – to 1:1 and 16:9: move and resize elements, keep timings.

REVIEW: 4 stills before the full render, then the critique loop (09-critique-loop.md).
```

## Tips

- Skärminspelningar: spela in i 1080×1920 eller högre; använd `device`-scenen i Motion Engine
  (mall `friskvard-portal-ad` / `friskvard-direct-ad`) om den passar – den gör redan det här.
- Bevistal som inte är verifierat: skriv om till "kolla med din arbetsgivare" eller visa en riktig
  skärmbild i stället.
