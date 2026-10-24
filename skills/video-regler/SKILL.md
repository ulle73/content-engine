---
name: video-regler
description: Rätt första gången för video, reels och animerade annonser – beslutsrunda före bygget, husregler för text, bild, slutkort och ljud som gäller utan att fråga, QA före leverans och en logg över lärdomar från beställarens feedback. Använd ALLTID när en video ska byggas eller ändras, tillsammans med studio.
---

# Video – rätt första gången

FAIV "Hitta faran" (2026-10-12) tog ett tjugotal ändringsrundor efter första leveransen. Nästan alla var
**smakbeslut som upptäcktes ett i taget efter rendering**: textens tempo och höjd, hur mörk bilden skulle vara,
vilka ljud och vilken musik, slutkortets tempo och streck. Därför:

1. **En beslutsrunda före bygget** – alla smakbeslut samtidigt, med varianter att jämföra.
2. **Husregler** som gäller utan att fråga (lärdomarna nedan).
3. **QA** som stoppar fel automatiskt innan leverans.
4. **Feedback blir regel direkt**, så samma sak aldrig behöver sägas två gånger.

## 1. Före allt

- Läs `skills/studio`, bolagets **brand-skill** och **faktaskill** (t.ex. `faiv-brand` + `faiv-fakta`,
  `golfkuponger-brand` + `golfkuponger-friskvard`) innan första förslaget.
- Sök i biblioteket – även teknikbanken (`find.py "<idé>" --type technique`, `skills/teknik`). Finns en verifierad mall för samma idé (t.ex. `faiv.template.hitta-faran` för mörker → ljus,
  före/efter med extraljus), börja i den. Den har redan alla beslut nedan inbyggda.

## 2. Beslutsrundan – en runda innan full rendering

Bygg ett beslutsunderlag och låt beställaren svara i **ett** meddelande (t.ex. "B, mörker 2, musik 1, H1, S5, ok slutkort"):

0. **Valda tekniker** ur teknikbanken (`skills/teknik`): krok, retention/struktur och cta – en rad var om varför.
1. **Manus och tidslinje räknade från läsregeln** → den verkliga längden. Blir filmen längre än önskat: föreslå
   textkortningar nu, inte efter leverans (FAIV-filmen gick från 24 till 39 s när läsregeln infördes i efterhand).
2. **Kontaktkarta i mobilstorlek** (en bild per beat, ~360 px bred) med texten på sina riktiga platser.
3. **Subjektiva nivåer som varianter sida vid sida** – synlighet för något dolt, gradering, mörker, hur tydlig en
   effekt är: tre nivåer i mobilstorlek. Bestäm aldrig en sådan nivå själv; den hamnar fel åt något håll.
4. **Ljudkarta och ljudprovning** enligt `skills/ljud`: musik (2–3 kandidater i sitt sammanhang, eller fråga om
   beställaren har en låt) och 3–6 numrerade kandidater per nyckelmoment.
5. **Slutkortet** färdigt: logga, rader, tajming och markering.

Först därefter full rendering. Efter leveransen ska bara finjusteringar återstå.

## 3. Husregler (gäller utan att fråga)

### Text
- **Läsregeln:** varje textbit syns minst max(5/6 s, tecken/12) + 0,9 s; text som läses i följd i en scen får
  lästiden för all text tillsammans, räknat från första biten (som `engine/edit/spec.py`). Gäller även i egna
  renderare – bygg in en kontroll som **stoppar renderingen** när regeln bryts.
> **Textplacering är en utgångspunkt, inte en strikt regel** (Jonas 2026-10-14): utgå från punkterna nedan om inget
> annat bestäms för filmen. Bestämmer beställaren något annat (t.ex. vänsterställd text eller text högst upp) gäller det
> – skriv beslutet i filmens `film.json` (`"beslut"`) och stäng av motsvarande kontroll med `"qa_av"`.

- **Allt som är centrerat ligger på bildens mitt, x 540** (Jonas 2026-10-24) – varje textrad, färgad ruta, etikett,
  logga och slutrad, med **samma marginal på båda sidor: minst 151 px** (högerkantens säkra marginal speglad). Det ger
  x 151–929 och högst 778 px bredd i 9:16; krymp text eller logga hellre än att flytta mitten. Centrera **aldrig** i den
  osymmetriska säkra ytan (mitt x ≈ 497): allt hamnar då 43 px åt vänster och ser snett ut.
  - En **färgad ruta** ska stå ensam på sin rad (`["ÖVER 60"]` i ruta, inte `ÖVER {60}`) – annars är raden centrerad
    men rutan, som ögat läser, hamnar snett. Räkna in rutans padding i bredden.
  - **Kontroll:** QA mäter mot x 540 (±12 px). Mät dessutom vänster = höger marginal i en bildruta ur leveransfilen.
- **En textposition, mer mot mitten:** all text utom slutkortet har första raden på samma höjd – 9:16: **y ≈ 560**
  (mitt i bild, inte högst upp; Jonas 2026-10-14), följande rader direkt under. Text som hoppar mellan topp, mitt och
  botten upplevs rörig. Undantag: när en logga eller ett motiv står mitt i bild ligger texten ovanför det (y ≈ 300).
  Slutkortet är centrerat.
- **Etiketter hör ihop med texten:** en etikett (t.ex. plats-ikon + bannamn) ligger centrerad **direkt under**
  huvudtexten med ett litet mellanrum (~40 px) – inte i en annan del av bilden.
- **Safe zones (Reels, 9:16, 1080×1920):** text, logga, produkt och allt annat viktigt (datum, belopp, etiketter) hålls
  borta från översta ~14 % (270 px), nedersta ~35 % (670 px), ~6 % (65 px) till vänster och **~14 % (151 px) till höger**
  – alltså inom x 65–929, y 270–1250. Högerkanten är bred för Facebooks knapprad; vi delar alltid på både Instagram och
  Facebook (Jonas 2026-10-14). Där ligger profilnamn, bildtext, knappar och CTA. Bara dekor (bakgrund, mark, partiklar) får
  gå utanför. Kontrollera med hjälplinjer på stillbilderna innan full rendering; i molnklippet kontrolleras det
  automatiskt (`edit-renderer/src/safezones.js`). Håll också texten utanför motivets
  viktiga delar.
- **Så stort som safe zones tillåter:** text och nyckelobjekt ska synas tydligt på mobilen. Mät radernas verkliga
  bredd i renderaren och sätt textstorleken per block så att den längsta raden fyller safe zone-bredden (~860 px, x 65–929);
  bryt hellre om raden än att krympa texten.
- Textanimationer: fade, lätt scale-in, tracking som dras ihop. Inga överdrivna övergångar.
- **Markerade ord (ord i färgad ruta):** ingen textskugga på texten i rutan – en mörk skugga på mörk text mot ljus ruta
  smetar ut bokstäverna. Rutan ska täcka hela versalhöjden inklusive Å/Ä/Ö-prickar och ringar.

### Bild
- **Något som ska vara svårt att se** (dolt rådjur, detalj): dämpa bara zonen runt det och kalibrera nivån med
  varianter (2.3). Mörka inte ner hela bilden eller sidorna. FAIV-rådjuret: 0,4 och 0,48 syntes för tydligt, 0,55 godkändes.
- **Vinjett** högst ~15 % i hörnen.
- Ta bort **andra varumärken** (märkestext och emblem på bilar, produkter) i reklam.
- Före/efter-bilder: kontrollera att de ligger exakt linjerade (korrelation/skillnad) och ändra aldrig innehållet.

### Slutkort
- **Har bolaget en färdig slutbild, används den sist i varje film** – även i egna renderare: Golfkuponger
  `edit-renderer/outros/golfkuponger/spotlight-<format>.mp4` (3,1 s, originalljud orört). Gör inget eget slutkort då.
- Bolagets **riktiga logga**, aldrig en textersättning.
- Alla rader in tätt efter varandra (≤ ~0,5 s emellan) – ingen lång väntan på URL:en.
- Markering och understrykning: **ren, tunn, en liten mjuk båge**, som ritas fram. Ingen slarvig penseltextur.
- Slutkortet får vara tyst. Musiken klingar ut vid övergången till slutkortet om inget annat sägs.

### Ljud
- Allt i `skills/ljud`: bara riktiga ljud, ljudprovning, effekter som accenter, -14 LUFS, stems.

### Leverans
- Film + stems (musik och effekter separat) + **manus** (`MANUS.md`: tidslinje med tider, text, bild, effekt,
  ljud, källor och licenser). Manuset skrivs från renderarens egna tider, inte ur minnet.

## 4. QA före leverans

Automatiskt i bygget: läsregeln, samma texthöjd, ljudsynk (ljud aldrig före bild – mät ansatsen vid varje
nyckelmoment), att musiken slutar där den ska, loudness (-14 LUFS, topp ≤ -1 dBTP), längd.
Sedan kritikloopen i `skills/studio` (kontaktkarta, mobilvy, strips runt snabba moment).
Säg alltid vad som **inte** är kontrollerat, t.ex. "jag har inte lyssnat".

## 5. Feedback blir regel – direkt

När beställaren rättar något som gäller fler filmer än denna: skriv in det **i samma session** här, i
`skills/ljud` eller i bolagets brand-skill, med datum och film. Spara en godkänd film som mall i
`library/templates/<namn>/` (med `LIBRARY.json`, förhandsvisning och `status: verified`).

## 6. Lärdomslogg

| Datum | Film | Beställarens feedback | Regel |
|---|---|---|---|
| 2026-10-12 | FAIV Hitta faran | "Texten rör sig väl fort" | Läsregeln i alla renderare, med stopp (3, Text) |
| 2026-10-12 | FAIV Hitta faran | Mörka bilden "omöjlig" att se, sedan för tydlig i två steg | Kalibrera synlighet med varianter; dämpa bara zonen (2.3, 3 Bild) |
| 2026-10-12 | FAIV Hitta faran | Texten än överst, än nederst, än i mitten | En textposition utom slutkortet (3, Text) |
| 2026-10-12 | FAIV Hitta faran | URL:en på slutkortet kom för sent; strecket "slarvigt" | Slutkortsrader tätt; ren tunn båge (3, Slutkort) |
| 2026-10-12 | FAIV Hitta faran | Syntljud "konstiga", ljud saknades på nyckelmoment, musiken skulle sluta vid loggan | `skills/ljud`; ljudkarta och provning i beslutsrundan (2.4) |
| 2026-10-12 | FAIV Hitta faran | "Detta tog alldeles för mycket edit" | Beslutsrunda före bygget (2), mall `faiv.template.hitta-faran` |
| 2026-10-13 | GK Årsskiftet | Slutbilden ska vara "slut" på alla klipp vi gör | Bolagets slutbild sist i varje film, även egna renderare (3, Slutkort) |
| 2026-10-13 | GK Årsskiftet | "Gör allt lite större så man ser det tydligare"; respektera safe zones | Safe zones x 65–1015, y 270–1250 för allt viktigt; text så stor som de tillåter (3, Text) |
| 2026-10-14 | GK Chefen betalar | "Det ska vara 14 %, på FB behövdes lite mer, vi delar alltid på både Instagram och FB" | Höger safe zone 14 % (x ≤ 929), vänster 6 % (3, Text) |
| 2026-10-14 | GK Spelat den här? | "Text kan generellt vara mer i mitten"; platstexten för långt från huvudtexten | Text y ≈ 560; etikett centrerad direkt under texten (3, Text) |
| 2026-10-14 | GK (alla) | "Text ska generellt vara mot mitten och centrerat" | Varje rad horisontellt centrerad i säkra ytan (mitt x ≈ 497) som utgångspunkt; QA kontrollerar, kan stängas av per film (3, Text) |
| 2026-10-24 | FAIV Kör du den här? (alla) | "Det ser så jävla fult ut när det ligger lite off" – text och logga låg 43 px åt vänster | Centrera på bildens mitt x 540 med lika marginal (≥ 151 px) båda sidor, aldrig 497; färgad ruta ensam på sin rad; QA mäter mot 540 (3, Text) |
| 2026-10-13 | GK Årsskiftet | "Man ser inte riktigt texten" (mörk text i ljus ruta) | Ingen skugga i markerade rutor; rutan täcker Å-ringen (3, Text) |
