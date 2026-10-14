---
name: film
description: Ändra eller bygga om en befintlig film i work/ (Golfkuponger m.fl.) – texter, ljudval, banor/bilder, tider – och göra nya filmer från en befintlig. Steg för steg så att vilken modell som helst gör det rätt: film.json, ./make.sh, automatisk QA och manuell granskning av kontaktarket. Använd ALLTID när någon vill ändra, justera, byta text/ljud/bana i, bygga om eller göra en variant av en film.
---

# Film – ändra och bygga filmer i work/

Varje film är ett **självständigt projekt i `work/<mapp>/`** (lokalt, inte i git). Översikt med alla filmer, status
och mappar: **`work/FILMER.md` – läs den först.** Gemensamma verktyg: `work/_verktyg/`. Banbilder: `work/_material/klubbar/`.

En film består av:
| Del | Fil | Ändras av dig? |
|---|---|---|
| **Inställningar** – texter, textstorlek, position, tider, ljudval, banor | `film.json` (Årsskiftet: `film-v1.json`, `film-spola.json`) | **Ja – nästan alltid bara här** |
| Bild/animation (ritar varje bildruta) | `src/*.js` | Bara om film.json inte räcker |
| Ljudmix | `audio*.py` (val via `"ljud"` i film.json) | Sällan |
| Bygg | `make.sh` → `../_verktyg/make-mall.sh` | Nej |

## Arbetsgång (följ i ordning)

1. **Hitta filmen** i `work/FILMER.md`. Gå till mappen (Git Bash). Årsskiftet tar `v1` eller `spola` först i varje kommando.
2. **Läs `film.json`.** Ändra bara de fält som beställningen gäller:
   - `"texter"`: `"rader"` (en sträng per rad, `{ord}` = ord i färgad ruta), `"storlek"` (px), `"topp"` (y för första raden), `"tid"` ([start, slut] i sekunder).
   - `"ljud"`: val ur ljudprovningen (t.ex. `"musik": "E1"`). Kandidaterna står i ljudskriptets topp och i `out/ljudprovning.mp4`.
   - `"banor"` (Spelat den här?): bana, namn, bildfil, `mitt_x` (utsnitt 0–1). Efter byte: `python -I prep.py`.
   - Spara som giltig JSON (svenska tecken som de är, UTF-8).
3. **Bygg bara det som behövs:**
   | Ändring | Kommando |
   |---|---|
   | Ljudval/nivåer | `./make.sh ljud` |
   | Text/storlek i en del av filmen | `./make.sh del <från s> <till s>` (ta med textens hela "tid" + 0,3 s marginal) |
   | Tider, banor, något som påverkar mycket | `./make.sh bild` |
   | Förhandsvisa först | `./make.sh bilder 3.0,8.5` → `out/kontakt.png` |
   | Ny ljudprovning | `./make.sh provning` |
4. **QA körs automatiskt** efter varje bygge (`./make.sh qa` för att köra igen). Läs `out/QA.md`:
   - Varje ❌ måste åtgärdas. Vanliga åtgärder: för lång text → kortare text eller längre `"tid"`; för bred rad →
     mindre `"storlek"` eller dela raden; utanför safe zone → ändra `"topp"`/`"storlek"`.
5. **Titta på `out/qa-kontakt.png`** (röda linjer = safe zones x 65–929, y 270–1250) och bocka av den manuella listan i
   QA.md. Öppna bilden och kontrollera på riktigt – rapportera vad du såg, inte "ser bra ut".
6. **Leverera:** filmens fil (`out/…-9x16.mp4`), vad som ändrats, QA-resultatet, och säg att ljud inte är avlyssnat.
   Uppdatera status i `work/FILMER.md` om något valts/godkänts.

## Regler som alltid gäller (källor: skills/video-regler, skills/ljud, skills/golfkuponger-brand, -friskvard)
- Läsregeln: varje text syns ≥ max(5/6, tecken/12) + 0,9 s – renderingen stoppar annars.
- Text 9:16 – **utgångspunkt, inte strikt regel**: varje rad horisontellt centrerad (mitt x ≈ 497 i säkra ytan); första
  raden y ≈ 560 (mot mitten); ovanför en logga/motiv i mitten y ≈ 300; etiketter centrerade direkt under texten.
  Har beställaren bestämt något annat för filmen gäller det: skriv det i `film.json` som `"beslut"` och stäng av
  kontrollen med `"qa_av": ["centrering"]` (möjliga: `"centrering"`, `"radbredd"`, `"safe-zone"`). Stäng aldrig av en
  kontroll utan ett sådant beslut.
- Safe zones: allt viktigt inom x 65–929, y 270–1250 (Instagram + Facebook).
- Fakta bara från faktabanken (31 december, köp direkt + pdf-kvitto, 300+ banor, "Låt chefen betala din golf"). Inga belopp.
- Ljud: bara riktiga ljud (ljudbanken `library/sounds`), -14 LUFS, topp ≤ -1 dBTP. AI kan inte lyssna – låt Jonas välja.
- Figurer: Tourleif (och Chefen) – rita aldrig nya figurer. Slutbilden (svingande logga) ligger alltid sist.
- Godkända val (ljud, banor, texter) ändras inte utan att beställaren bett om det.

## Ny film från en befintlig
`../_verktyg/ny-film.sh <ny-mapp> <från-mapp>` → ändra `film.json`, byt filnamnet `FILM=` i `make.sh`, `./make.sh bild`,
granska QA, lägg till raden i `work/FILMER.md`. Helt nya idéer: börja i `skills/studio` och `skills/video-regler`
(beslutsrunda med manus och stilbilder innan bygget).

## Vanliga fel (lärdomar – undvik)
- **Ändra inte i `src/film-config.js`** – den skrivs om från film.json vid varje bygge.
- **Okänt text-id i film.json** stoppar bygget med en lista över giltiga id:n – använd dem.
- **Bilder som ritas om varje bildruta** måste ligga som fasta `<symbol>` (laddas en gång), annars blir rutor tomma.
- **Namnkrock i JS:** filerna laddas som vanliga skript i samma scope – nya globala namn (`const PH`) kan krocka. Ger
  "TEXTS tom"/fel texter i läsregeln. Byt namn.
- **Ljudnivå:** nivåsätt ett ljud mot dess **starkaste** del – en tyst början gav +40 dB en gång. Kör `./make.sh ljud` och läs nivåerna.
- **Textskugga** i färgade rutor gör texten oläslig – rutorna har ingen skugga; rör inte det.
- **work/ ligger inte i git** – radera aldrig mappar i work/ utan att fråga.
