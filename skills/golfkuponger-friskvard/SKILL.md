---
name: golfkuponger-friskvard
description: Affärskunskap om Golfkuponger och friskvårdsbidraget – köpvägar (förmånsportaler som Epassi/Benify och direktköp), godkända påståenden, säsong, målgrupper, vinklar och smarta frågor. Använd ALLTID när en annons, idé, copy eller kampanj för Golfkuponger rör friskvård, friskvårdsbidrag, förmånsportal, Epassi, Benify, arbetsgivare, "brinner inne", årsskifte eller företagskuponger.
---

# Golfkuponger – friskvård

Den här skillen gör att idéerna blir *Golfkupongers* och inte generiska. Den har två delar: **fakta** (vad vi får säga) och **idémotor** (frågor, vinklar, storyboard-mönster).

## Regel nummer ett: bara godkända påståenden

Allt som visas eller sägs i en annons och som är ett faktapåstående läggs i `AdBrief.facts` med källa. `verified: true` får bara sättas för rader med status ✅ nedan. Är du osäker, omformulera till något som inte är ett påstående ("kolla med din arbetsgivare") eller fråga Jonas.

### Faktabank

| # | Påstående | Källa | Status |
|---|---|---|---|
| F1 | Golfkuponger finns att köpa i förmånsportaler. Nämnda i repot: Epassi, Benify/Benifex, Söderberg & Partners | `engine/motion/planner.py`, minne | ⚠️ Verifiera exakt aktuell portallista |
| F2 | Det går att köpa direkt på golfkuponger.se och få kvitto från Golfkuponger, för den som saknar förmånsportal | mall `friskvard-direct-ad` | ⚠️ Verifiera formulering om kvitto/underlag |
| F3 | Köpvägen i portalen: sök Golfkuponger → välj belopp → koden läggs in i appen | mall `friskvard-portal-ad` | ⚠️ Verifiera mot aktuell portal |
| F4 | Golf på "300+ klubbar" | mall `friskvard-portal-ad` | ⚠️ Verifiera aktuellt antal |
| F5 | Kupongerna kan användas "hela nästa säsong" | mall `friskvard-portal-ad` | ⚠️ Verifiera giltighetstid |
| F6 | Friskvårdsbidraget "brinner inne 31/12" | standardhook i mallen | ⚠️ Gäller per arbetsgivare, inte universellt. Se nedan |
| F7 | Skattefri nivå och vad som räknas som friskvård | Skatteverket | ❌ Använd inte förrän formulering är verifierad mot Skatteverket och juridiskt OK |

*Fyll i, uppdatera och ändra ⚠️ → ✅ när du har verifierat. Lägg till datum och källa.*

### Formuleringar som är säkra utan verifiering

- "Kolla hur mycket friskvårdsbidrag du har kvar."
- "Har du bidrag kvar i år?"
- "Gör ditt friskvårdsbidrag till golf."
- "Sök på Golfkuponger i din förmånsportal." (förutsatt F1)

### Undvik

- Absoluta deadlines för alla ("alla förlorar sitt bidrag 31/12"). Skriv i stället "för många" eller "hos de flesta", eller "innan årsskiftet" kombinerat med "kolla med din arbetsgivare", om det är verifierat.
- Skatte- eller juridiska påståenden (F7) utan verifiering.
- Jämförelser med namngivna konkurrenter.
- Att återskapa portal-, app- eller kvitto-UI med AI. Använd riktiga skärminspelningar.

## Två köpvägar = två annonsspår

| Spår | Målgrupp | Remotion-mall | Bärande budskap |
|---|---|---|---|
| **Portal** | Anställda vars arbetsgivare har en förmånsportal | `friskvard-portal-ad` (15 s, 5 assets) | "Sök Golfkuponger i din portal" |
| **Direkt** | Anställda utan portal, som får bidraget mot kvitto | `friskvard-direct-ad` (14 s, 4 assets) | "Ingen portal? Köp direkt, få kvitto" |

Vet du inte vilket spår som gäller, fråga. Det avgör mall, bilder och copy.

Utan krav på skärminspelningar fungerar även `golf-sista-chansen` (brådska) och `golf-fracka` (rolig och fräck) för friskvårdsbudskap. Se tonregistret i `golfkuponger-brand`.

## Säsong (vinklar, inte fakta)

- **Okt–dec**: "Brinner inne", sista chansen, julklapp till dig själv. Högsta trycket.
- **Jan–feb**: nytt bidrag och nytt år, planera säsongen.
- **Mar–maj**: säsongsstart, "första rundan".
- **Jun–sep**: mitt i säsongen, spela fler banor och ta med kollegor.

## Idémotor

### Smarta frågor (max 3, alltid med förslag)

Ställ bara de frågor som saknas i `AdBrief.missing()`, och ge färdiga svarsförslag som knappar.

1. **Spår**: "Portal, direktköp eller båda?" → [Portal] [Direkt] [Båda, två varianter]
2. **Målgrupp**: "Vem pratar vi med?" → [Golfare med bidrag kvar] [Nybörjare som är nyfikna] [HR/arbetsgivare]
3. **Känsla**: "Vilken ton?" → [Lugn påminnelse] [Brådska/sista chansen] [Inspiration/sugen på golf]
4. **Format**: "Var ska den gå?" → [Reels/Stories 9:16] [Feed 4:5] [Alla]

Fråga aldrig om sådant som redan sagts, och aldrig mer än tre saker åt gången.

### Vinkelbibliotek ("brinner inne")

Föreslå alltid tre vinklar som skiljer sig åt på riktigt, inte tre varianter av samma.

| Vinkel | Hook (≤8 ord) | Varför |
|---|---|---|
| Pengarna försvinner | "DITT FRISKVÅRDSBIDRAG BRINNER INNE" | Förlustaversion, tydligast |
| Du har redan betalat | "PENGAR DU REDAN HAR. ANVÄND DEM." | Omramar bidraget till "dina pengar" |
| Nästa säsong, nu | "KÖP NÄSTA SÄSONGS GOLF I ÅR" | Löser problemet att det inte är golfsäsong i december |
| Tre klick | "GOLF FÖR BIDRAGET. TRE KLICK." | Tar bort friktion med portal-flödet |
| Kollegan visste | "KOLLEGAN SPELAR GOLF FÖR SITT BIDRAG" | Socialt bevis och FOMO |

### Storyboard-mönster (6–15 s)

1. **Hook** (0–2 s): problemet eller löftet i ≤8 ord, rörelse från frame 0.
2. **Hur** (2–8 s): riktiga skärminspelningar av köpvägen, en handling per scen.
3. **Bevis** (2 s): banbild och ett verifierat siffer-/nyttopåstående.
4. **CTA** (2 s): slutkort enligt `golfkuponger-brand`.

### Bildval ur banken

Matcha på taggar i denna ordning: spår (portal/direkt) → scenroll (hook/screen/proof) → säsong → stämning. Hook-bilden ska ha rörelse eller en människa i aktion. Proof-bilden ska vara en bred, vacker bana. Föreslå 2–3 kandidater per roll och låt Jonas välja. Saknas en riktig skärminspelning för vald portal, säg det och be om uppladdning. Generera den aldrig.
