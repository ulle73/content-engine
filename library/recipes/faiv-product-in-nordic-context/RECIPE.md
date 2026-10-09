# Grillkitet på plats – nordisk miljö (`faiv-product-in-nordic-context`)

**FAIV · product-in-context · 15 s · 9:16 (4:5, 1:1) · status: draft · pilotrecept (MASTERPLAN §4b)** · [`recipe.json`](recipe.json)

## Idén

En verklig människa vid sin Volvo/Tesla visar FAIV:s grillkit i svensk vintermiljö – sedan tänds ljuset. Produkten är
alltid exakt (riktigt foto/film), miljön och stämningen kan lyftas med AI. Det här är receptet som produktionsmotorns
pilot bygger end-to-end.

**Krok:** *"Din {car_model} – fast som den borde sett ut från fabrik."* (vinkel från `faiv-fakta`).

## Scen för scen

| # | Tid | Material | Regi |
|---|---|---|---|
| s1 hook | 0–2,5 | `fa-b4`, `fa-n1` | Bilen parkerad i snö/skog vid blå timmen, låg vinkel, långsam push mot fronten. |
| s2 människa | 2,5–5,5 | `fa-b2`, `fa-h1` | Ägaren hukar vid fronten och pekar på grillen. Handhållen halvbild, mjuk båge åt höger. |
| s3 produkt | 5,5–8 | **produktfoto** (`catalog_query: "grillkit {car_model}"`) | Ken Burns + ljussvep på katalogbilden; `{product}` som rubrik. Finns `fa-p1` filmat → använd det. |
| s4 reveal | 8–11 | `fa-m1` | Stativ, ljuset på – hårt klipp på dropet. Aldrig AI. |
| s5 rörelse | 11–13 | `fa-b3` | Bilen kör förbi med ljud, snödamm i ljuset. |
| s6 cta | 13–15 | grafik | *"{product} · {fact:F4}"* (garanti bara om verifierad). Logga blur-reveal. |

## Klipprytm

~96 BPM, filmisk. Första halvan långsamma rörelser (push, båge), andra halvan på slag. Dropet ligger på s4.

## Text och ljud

Kroken i två rader, sedan bara produktnamnet. Prisvariant: `{fact:F5}`/`{fact:F6}`/`{fact:F7}` – verifieras före **varje** annons.
Ljud: vind, snö under fötterna, klick + boom på ljuset, motor vid förbifarten.

## AI-uppgraderingar – så slottar de in (D10 + D12)

1. **gpt-image-2** bygger en 9:16-komposit: riktig person + riktig bil + **exakt produktfoto** från `search_products` /
   `use_product_images` (se `library/models/gpt-image-2/PLAYBOOK.md`, exempel 1).
2. **Seedance** (s1, s2) animerar kompositen: människan rör sig, kameran åker, produkten står still.
3. **Kling** (s5) gör förbifarten från ett riktigt still av bilen med tänt ljus.
4. s4 är **alltid** riktig film.

Vision-QA per klipp: produktens form/LED/logga identisk med katalogbilden, händer, inga regskyltar.

## Varianter

- Sommar/semester-vinkeln (jun–aug): grillkit till nya bilen, ljus kväll vid sjö.
- Arbetsfordon: Vito/Sprinter med grillkit (`{fact:F7}`), hantverkare som huvudperson.
- Ingen person tillgänglig: hoppa över s2, förläng s1 och s3.
