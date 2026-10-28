# Golfare i &lt;stad&gt;? – stillbild, slam och snurr (9:16)

Lokal stadsannons för Golfkuponger. Bygger på Meta-genomgången 2026-10-28: "Golfare i Stockholm/Göteborg?" på ett riktigt
banfoto med en närliggande klubb var de billigaste annonserna per kundvagn. Byggdes för A/B-test 01 (stillbild mot rörligt).

En annons ger tre filer som **bara skiljer sig i rörelse**. Stillbilden är exakt slutbilden i båda filmerna, och
`rendera.mjs` stoppar om den inte är det:

| | Vad händer |
|---|---|
| **A – stillbild** | GOLFARE I / STAD? (staden i guld med 3D-djup), "Spela **Klubb** och N+ andra …" (klubben i guld), knapp "Hitta din bana →", loggan |
| **B1 – slam** | Orden slår ner ett i taget med djup och kameraryck, guldglans på staden |
| **B2 – snurr** | GOLFARE I slår ner, stadsnamnet rullar som en enarmad bandit och landar på staden |

I båda filmerna rullar sedan klubbnamnet i underraden genom ett tolvtal andra klubbar i regionen – varje namn står
still så länge att det hinner läsas, kortare först och längre mot slutet – och landar ~6,4 s på den utvalda klubben,
som blinkar ljusare guld. Därefter poppar knappen.

Filmerna är 10,4 s (längre om texten kräver det enligt läsregeln) + Spotlight-slutbilden 3,1 s. Guldytan i rubriken
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
| `klubbrulle` | nej | Klubbarna som rullar förbi i underraden. Standard: `antal_rulle` (12) andra golfbanor i regionen ur klubblistan, jämnt spridda, med korta namn ("Bro Hof Slott GC" → "Bro Hof Slott") |
| `antal_rulle` | nej | Hur många klubbar som rullar förbi (standard 12) |
| `rad1`, `underrad`, `knapp` | nej | Annan text. `underrad` får innehålla `{klubb}` och `{antal}` |
| `namn`, `filnamn` | nej | Filnamn. `filnamn` med `{variant}`, t.ex. `"T01_format_{variant}_sthlm"` |

```bash
python ../../library/sounds/sounds.py copy sound.hallelujah-kor musik/hallelujah-kor.mp3
node rendera.mjs annonser/goteborg.json --musik musik/hallelujah-kor.mp3 --traff 2.48
node rendera.mjs annonser/goteborg.json --bara-still      # bara stillbilden, på några sekunder
```

Ut: `resultat/<stad>/…_A-still.jpg`, `…_B1-slam.mp4`, `…_B2-snurr.mp4`. Kontaktkartor och safe zone-kontroll i `out/<stad>/`.

### Antal klubbar i regionen

Räknas ur golfkuponger.se:s klubblista (`klubbdata/klubbar-sajt-2026-10-21.json`): aktiva golfbanor i stadens region, klubben själv
oräknad, avrundat nedåt till närmaste 5. Stockholmsområdet har 39 → "Kallfors och 35+ andra". Göteborgsområdet har 23
→ "20+". Byt listan när sajten ändras (samma format som i `work/gk-sa-funkar-det/karta/`). Varnar om klubben inte finns i regionen.

### Musik och träffpunkt

`--traff <s>` är tiden **i musikspåret** som ska slå exakt när stadsnamnet landar (B1 0,95 s, B2 1,75 s in i filmen).
Skriptet förskjuter spåret per variant, tonar ut vid slutbilden och normaliserar till -14 LUFS (topp ≤ -1,5 dB).

| Ljud (ljudbanken) | `--traff` | Effekt |
|---|---|---|
| `sound.hallelujah-kor` (Pixabay, 8,7 s) | `2.48` | Första frasen under rullen, en kort paus precis före, sedan HALLELUJA! när staden landar. **Används i test 01.** |
| `music.hallelujah-handel-1916` (Händel, Oratorio Chorus 1916, public domain) | `6.61` | Orkesterintro under rullen, kören sätter in på landningen. Gammal inspelning med brus |

## QA i bygget

Läsregeln (all text från första biten), safe zones (allt inom y 270–1250, centrerat på x 540 med lika marginal),
rubriken krymper tills knappen ryms ovanför y 1250, stillbilden = slutbilden i båda filmerna (PSNR), filerna går att avkoda.
Ej automatiskt: att bilden är snygg i 9:16 med valt `fokus` – titta på `resultat/<stad>/…_A-still.jpg`.
