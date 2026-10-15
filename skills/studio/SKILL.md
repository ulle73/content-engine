---
name: studio
description: Ingången för allt innehåll som ska skapas – video, reels, annonser, karuseller, animationer, motion graphics, explainers, musikvideor, bilder och copy. Använd ALLTID först, innan något byggs från noll. Söker i Content Library (library/catalog.json) efter färdiga, snygga och verifierade mallar, effekter, övergångar, textbehandlingar, karusellstilar, skills och prompts, föreslår 2–3 kombinationer med förhandsvisning och anpassar sedan det valda till det användaren vill ha.
---

# Studio – börja alltid från något snyggt

Allt nytt innehåll börjar i biblioteket. Vi bygger aldrig från noll när det finns en färdig mall,
effekt eller stil som kan anpassas. Det finns inga stilregler här: allt får användas och
kombineras – glitch, whips, 3D, morphs, hårda klipp, studs, vilka typsnitt och hur mycket text
som helst. Brand-skillen (`golfkuponger-brand`, `faiv-brand` …) är ett **utgångsläge**, inte en spärr.

**Video ska bli rätt första gången:** följ `skills/video-regler` – en beslutsrunda med alla smakbeslut
före full rendering, husregler (lästid, en textposition, slutkort, ljud) och QA före leverans.

## 1. Förstå beställningen (max 3 frågor, alltid med förslag)

Fråga bara det som saknas: vad (video, karusell, bild …), var den ska gå (format: 9:16 / 1:1 /
4:5 / 16:9), längd, känsla eller en referens ("som den här videon"), och vilket material som
finns (bilder, logga, skärminspelningar, musik). En referens lyfter resultatet mest – be om en.
Läs bolagets brand- och faktaskill (`skills/<bolag>-brand`, faktabanken) innan första förslaget.

## 1b. Utgå från en referens som fungerar

Har beställaren en **videolänk** ("gör en sån här för FAIV"), eller ska vi göra vår version av något som går bra hos
konkurrenterna: börja i referensen, inte i en tom mall.

- **Länk** (Meta Ad Library, Instagram, TikTok, YouTube, Facebook, direktlänk) → MCP `analyze_reference_video`
  (lokalt: `python manage.py reference_lab --company Faiv --url <länk> --adapt`).
- **Bevakade annonser** → `list_reference_candidates`: annonser som gått längst (= de tjänar pengar) och störst
  EU-räckvidd först. Lokalt: `reference_lab --top 3`.
- Nedbrytningen ger scen för scen med exakta tider (uppmätta, inte gissade): krok, struktur, kamera, text, tal,
  musik, ljud, tempo och varför den fungerar. Visa kontaktkartan (`view_reference_sheet`).
- `plan_our_version` gör **vår version** för bolaget: samma grammatik, vår vinkel, bara verifierade fakta, material ur
  mediabanken eller en konkret inspelningslista, och närmaste recept. Fortsätt sedan i beslutsrundan (avsnitt 4).
- Vi lånar krok, struktur, rytm, kameraspråk och ljudgrepp – **aldrig** referensens bilder, personer, formuleringar,
  musik, varumärke eller påståenden.

## 2. Sök i biblioteket

```bash
python library/tools/build_catalog.py          # om catalog.json saknas eller är gammal
python library/tools/find.py "<ord från beställningen>" --format 9:16 --limit 20
python library/tools/find.py "<ord>" --type template --verified
python library/tools/find.py "<ord>" --type transition
python library/tools/find.py "<bolag + idé>" --type recipe    # video: produktionsrecept per bolag
python library/tools/find.py "<scentyp>" --type model         # vilken AI-modell per scen + promptformat
python library/tools/find.py "<idé> krok" --type technique    # bevisade tekniker: krok, retention, cta, struktur
```

**Tekniker först (obligatoriskt för varje video och karusell):** välj 1 krok + 1 struktur/retention + 1 cta ur
teknikbanken enligt `skills/teknik` (A) och motivera valet i förslaget. Skickar beställaren en länk med en teknik som
ska sparas: `skills/teknik` (B).

För **film** börjar du helst i ett recept (`library/recipes/<id>/RECIPE.md` + `recipe.json`): scener med
filmlista-id:n (`docs/FILMLISTA.md`), effekter, ljud och valfria AI-uppgraderingar per scen. Receptet är ett förslag –
blanda och bryt fritt.

Sök flera gånger: en **bas** (`template`, `carousel` eller en `skill`), **effekter/övergångar**
(`effect`, `transition`, `background`, `grade`), **text** (`text`, `caption`), **ljud** (`sound`)
och **prompts** (`prompt`, t.ex. regissörsbrief och kritikloop). Bläddra visuellt i
`library/gallery.html`. Verifierade poster med förhandsvisning går först.

## 3. Föreslå 2–3 kombinationer

Varje förslag: tekniker (krok/retention/cta) + basmall + 2–4 effekter/övergångar + textbehandling + ljud, med id:n och
förhandsvisningar (`library/previews/…`). Säg varför de passar. Låt användaren välja eller
blanda. Ingen beställning ska få samma tre förslag – variera stil på riktigt.

## 4. Beslutsrunda (video) – innan full rendering

Visa i ett svar: manus och tidslinje räknade från läsregeln (verklig längd), kontaktkarta i mobilstorlek,
subjektiva nivåer som tre varianter sida vid sida, ljudkarta och ljudprovning, och det färdiga slutkortet.
Beställaren svarar med sina val i ett meddelande. Detaljer: `skills/video-regler` avsnitt 2.

## 5. Bygg från det valda

Varje post har `use` som säger hur den körs: en skill (`/live-carousel`, `/animate`,
`/motiongraphics`, `/carousel-kit`, `/persa-short-editing`, `/motion-studio`, `/hyperframes` …),
ett komponentblock att kopiera in, eller en prompt att fylla i. Arbetsfiler och renderingar
läggs i `work/` (inte i git). Golfkuponger-material: `skills/golfkuponger-brand` (färger,
typsnitt, logga, bildspråk som utgångsläge) och `skills/golfkuponger-friskvard` (köpvägar,
vinklar och faktabank).

**Fakta:** påståenden i reklam ska komma från faktabanken (`golfkuponger-friskvard`). Säg till
om något är overifierat.

**Ljud:** följ `skills/ljud` för all musik, alla ljudeffekter och all mixning. Hårda regler: bara riktiga
ljud (aldrig ljudeffekter syntetiserade i kod), få ljud, ljudprovning innan något spikas (AI:n kan inte
lyssna), -14 LUFS och topp ≤ -1 dBTP vid leverans, leverera musik och effekter som separata stems.

## 6. Kritikloop innan leverans

Rendera en kontaktkarta (en bild per beat), en mobilvy (~360 px bred) och strip runt snabba
moment. Titta på dem. Sätt poäng 1–10 på: krok första 2 s, läsbarhet på mobil, rörelsekvalitet,
variation (något nytt var 2–4 s), komposition, varumärke, ljud (hierarki, synk och nivåer enligt
`skills/ljud`). Fixa de tre sämsta, upprepa
tills allt är 8+. Mall: `library/prompts/motion-studio-playbook/` (kritikloop).

## 7. Låt biblioteket växa

Blev resultatet bra: spara det som ny mall i `library/templates/<namn>/` med förhandsvisning
och en post i `LIBRARY.json` (`status: verified`), kör `build_catalog.py`. Nästa gång börjar
någon därifrån. **Godkända ljud** (även musik och ljud beställaren skickat) sparas i ljudbanken `library/sounds/`
(se `skills/ljud`), och mallen hämtar dem därifrån. Återanvändbara delar (en figur, en effekt, en övergång) får egna
poster i mallens `LIBRARY.json` så att de hittas med `find.py`. Rättade beställaren något som gäller fler filmer: skriv in det som regel i
`skills/video-regler` (lärdomsloggen), `skills/ljud` eller brand-skillen i samma session.
