# Golfare i &lt;stad&gt;? – stillbild, slam och snurr (9:16)

Lokal stadsannons för Golfkuponger. Bygger på Meta-genomgången 2026-10-28: "Golfare i Stockholm/Göteborg?" på ett riktigt
banfoto med en närliggande klubb var de billigaste annonserna per kundvagn. Byggdes för A/B-test 01 (stillbild mot rörligt).

En annons ger tre filer som **bara skiljer sig i rörelse**. Stillbilden är exakt slutbilden i båda filmerna, och
`rendera.mjs` stoppar om den inte är det:

| | Vad händer |
|---|---|
| **A – stillbild** | GOLFARE I / STAD? (staden i guld med 3D-djup), "Spela **Klubb** och N+ andra …" (klubben i guld), loggan – blocket centrerat i bilden. Ingen knapp i bilden (Metas egen räcker) |
| **B1 – slam** | Orden slår ner ett i taget med djup och kameraryck, guldglans på staden |
| **B2 – snurr** | GOLFARE I slår ner, stadsnamnet rullar som en enarmad bandit och landar på staden |

I båda filmerna rullar sedan klubbnamnet i underraden genom regionens **5 största klubbar** (`klubbdata/stora-klubbar.json`,
den största sist – Djursholms GK, Stockholms GK, Arlandastad, Ullna, Bro Hof i Stockholm), **0,6 s per klubb**, så att
Halleluja-kören räcker hela vägen (Jonas 2026-10-28) – varje namn står
still så länge att det hinner läsas, kortare först och längre mot slutet – och landar ~6,4 s på den utvalda klubben,
som blinkar ljusare guld. Därefter poppar knappen.

Nere till vänster står alltid en plats-ikon och banans namn i litet format, så att man ser vilken bana bilden är
(Jonas 2026-10-28; y 1500 – under säkra ytan, så bildtexten i Reels kan skymma den). Scenen slutar när knappen har landat (~7,5 s) och klipper direkt till Spotlight-slutbilden (3,1 s), där musiken tonar ut –
totalt ~10,7 s. Ingen tyst, stillastående tid före slutbilden (Jonas 2026-10-28). Läsregeln räknar ~10 s för texten; QA varnar
men stoppar inte (`"lasregel": "stopp"` i annonsen gör den hård, `"langd": <s>` sätter scenens längd). Guldytan i rubriken
täcker prickar och ringar på Å/Ä/Ö (Göteborg).

## Ny stad

```bash
cp -r library/templates/golfkuponger-golfare-i-stad work/golfare-i-stad    # en gång; alla städer i samma mapp
cd work/golfare-i-stad
```

Skriv `annonser/<stad>.json`:

```json
{
  "stad": "Göteborg",
  "klubb": "Sankt Jörgen",
  "bild": "work/_material/klubbar/scrape/Sankt Jörgen Park Golf/01_2048x1365.webp",
  "fokus": 0.55
}
```

| Fält | Krävs | Vad |
|---|---|---|
| `stad` | ja | Staden i rubriken. Blir `STAD?` och sista ordet i rullen |
| `klubb` | ja | Klubben i underraden ("Spela **Kallfors** och 35+ andra …") |
| `bild` | ja | Banfotot, relativt annonsen eller repots rot. Alla bilder i `work/_material/klubbar/` får användas i reklam |
| `fokus` | nej | Var bilden beskärs till 9:16: 0 = vänsterkant, 1 = högerkant (stående foton: topp–botten). Standard 0,5 |
| `antal` | nej | Skriv över antalet, t.ex. `"40+"`. Annars räknas det ut (nedan) |
| `region` | nej | Om staden inte finns i `REGION` i `rendera.mjs`: en av sajtens regioner |
| `rulle` | nej | Städerna som rullar förbi i B2. Standard: åtta andra storstäder |
| `bana` | nej | Banans namn nere till vänster vid plats-ikonen. Standard: klubbens fulla namn ur klubblistan ("Kallfors GK") |
| `klubbrulle` | nej | Klubbarna som rullar förbi i underraden. Standard: `antal_rulle` (12) andra golfbanor i regionen ur klubblistan, jämnt spridda, med korta namn ("Bro Hof Slott GC" → "Bro Hof Slott") |
| `antal_rulle` | nej | Antal klubbar i rullen (standard 5, de största); fylls på om regionens lista är kortare |
| `klubb_tid` | nej | Sekunder per klubbnamn i rullen (standard 0,6). Längre rulle = längre film; Halleluja-kören räcker till ~8,7 s |
| `plats_y` | nej | Var banans namn står (standard y 1500, under säkra ytan – beslut Jonas 2026-10-28) |
| `forsprang` | nej | Sekunder innan första ordet slår ner (standard B1 0,5, B2 0,68), t.ex. `{"1": 0.5, "2": 0.68}` |
| `rad1`, `underrad` | nej | Annan text. `underrad` får innehålla `{klubb}` och `{antal}` |
| `knapp` | nej | Knapptext i bilden, t.ex. `"Hitta din bana →"`. Standard: ingen knapp (Jonas 2026-10-28; de stora annonsörerna har ingen, Metas egen knapp räcker) |
| `mitt_y` | nej | Blockets mitt (standard 960 = bildens mitt; flyttas upp om säkra ytan, y 1250, annars passeras) |
| `namn`, `filnamn` | nej | Filnamn. `filnamn` med `{variant}`, t.ex. `"T01_format_{variant}_sthlm"` |

```bash
python ../../library/sounds/sounds.py copy sound.hallelujah-kor musik/hallelujah-kor.mp3
node rendera.mjs annonser/goteborg.json --musik musik/hallelujah-kor.mp3 --traff 2.48 --traff-b1 1.32
node rendera.mjs annonser/goteborg.json --bara-still      # bara stillbilden, på några sekunder
```

Ut: `resultat/<stad>/…_A-still.jpg`, `…_B1-slam.mp4`, `…_B2-snurr.mp4`. Kontaktkartor och safe zone-kontroll i `out/<stad>/`.

### Antal klubbar i regionen

Räknas ur golfkuponger.se:s klubblista (`klubbdata/klubbar-sajt-2026-10-21.json`): aktiva golfbanor i stadens region, klubben själv
oräknad, avrundat nedåt till närmaste 5. Stockholmsområdet har 39 → "Kallfors och 35+ andra". Göteborgsområdet har 23
→ "20+". Byt listan när sajten ändras (samma format som i `work/gk-sa-funkar-det/karta/`). Varnar om klubben inte finns i regionen.

### Musik och träffpunkt

`--traff <s>` är tiden **i musikspåret** som ska slå exakt när stadsnamnet landar (B1 0,95 s, B2 1,75 s in i filmen).
Skriptet förskjuter spåret per variant och låter musiken fortsätta 0,45 s in i slutbilden, där den tonar ut till ~8 s –
en kort paus innan svingloggans eget ljud (~1,17 s in i slutbilden). Räcker spåret inte dit saktas det ned (högst 12 %,
tonhöjden behålls) så att träffen ändå hamnar rätt. Normaliseras till -14 LUFS (topp ≤ -1,5 dB). `"musik_in_i_slutbild": <s>` ändrar övergången.

| Ljud (ljudbanken) | `--traff` | Effekt |
|---|---|---|
| `sound.hallelujah-kor` (Pixabay, 8,7 s) | `2.48`, `--traff-b1 1.32` | Kören börjar från första tonen; i B2 kommer andra frasen exakt när staden landar, i B1 betoningen i första frasen. **Används i test 01.** |
| `music.hallelujah-handel-1916` (Händel, Oratorio Chorus 1916, public domain) | `6.61` | Orkesterintro under rullen, kören sätter in på landningen. Gammal inspelning med brus |

## QA i bygget

Läsregeln varnar (all text från första biten), safe zones (allt inom y 270–1250, centrerat på x 540 med lika marginal),
rubriken krymper tills knappen ryms ovanför y 1250, stillbilden = slutbilden i båda filmerna (PSNR), filerna går att avkoda.
Ej automatiskt: att bilden är snygg i 9:16 med valt `fokus` – titta på `resultat/<stad>/…_A-still.jpg`.
