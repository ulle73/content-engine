---
name: bang-motion
description: Bang Motion – motion graphics i webbläsaren (HTML + CSS + GSAP, ev. Three.js) som rör sig som film, inte som bildspel. Openers, promos, bumpers, kinetisk typografi och sex explainerstilar i 9:16 eller 16:9, en index.html som renderas bildruta för bildruta till MP4. Använd när en video ska kännas filmisk med EN sammanhängande värld och en kamera som rör sig, när ett utkast ser ut som PowerPoint/slides, eller när du vill ha en meny av öppningskoncept (19) och stilriktningar (10). Gå via /studio och /teknik först; Golfkupongers videoregler gäller över Bang Motions egna.
license: MIT (Bang Tutorial, https://github.com/bangtutorial/bang-motion, v1.19.0)
---

# Bang Motion (importerad, svensk ingång)

Originalet är skrivet på **indonesiska** och ligger orört i `references/ORIGINAL-SKILL.md` – läs det, det är skillens
hjärta (lagar, arbetsflöde, checklista). Den här filen säger hur det används i content-engine och vad som gäller
**över** originalet. Importen beskrivs i `library/kits/bang-motion/IMPORT-NOTES.md`.

## Före första raden

1. `/studio` och `/teknik` (krok, retention, cta) som vanligt – Bang Motion är en mall/teknik i biblioteket, inte en genväg förbi dem.
2. Läs `skills/video-regler` och slutkortsavsnittet i `skills/golfkuponger-brand`. Beslutsrundan (idé, text, tidslinje) innan full rendering.
3. Läs i originalet: `## Larangan struktural` (PPT-testet, 8 punkter), `## Hukum #1–#4`, `## Alur kerja`, `## Checklist sebelum menyerahkan`.
4. Välj koncept och stil ur menyerna nedan och skriv en kort stilbrief (3 kandidater, 1 rekommendation, palett med källa per färg) – det är Bang Motions eget steg och passar vår beslutsrunda.

## Våra regler går före originalet

| Bang Motion säger | I content-engine gäller |
|---|---|
| 16:9 som standard | **9:16 (1080×1920)** för IG/FB om inget annat sägs (`W=1080,H=1920`) |
| Safe area `.safe{transform:scale(.78)}` (≈190 px topp, 230 px botten) | **Våra safe zones:** topp 14 %, botten 35 %, sidor 6 %, höger 14 %. Text centrerad på x 540, första raden y ≈ 560 |
| Egen slutlogga/CTA | **Spotlight-slutbilden sist** (3,1 s), sista bilden tonar till `#0c140f`; läggs på efter exporten med ffmpeg |
| Ingen ljudregel | Ljud enligt `skills/ljud` (aldrig syntade SFX, ljudprovning). Exporten är tyst – ljudet läggs på MP4:an |
| Textlängd "kort" | **Läsregeln** på all text i scenen: max(5/6 s, tecken/12) + 0,9 s |
| Bilder via Higgsfield MCP (betalt) | Först egna: godkända banbilder (KLUBBAR), Tourleif/Chefen-modulerna, frilägg med `npx hyperframes remove-background`/rembg. Betalt bara efter fråga |
| Fakta i texten | Påståenden i reklam kommer från faktabanken (`skills/golfkuponger-friskvard`) |
| Banfoto | Plats-ikon + banans namn smått nere till vänster (x 65, y ~1500) |

Stilreglerna i Bang Motion (PPT-testet m.m.) är **starka tips**, inte spärrar – men ett utkast som faller på PPT-testet
ska byggas om innan Jonas ser det.

## Arbetsflöde här

```bash
mkdir -p work/bang-motion/<projekt>
cp .claude/skills/bang-motion/assets/starter-<stil>.html work/bang-motion/<projekt>/index.html   # sätt W=1080,H=1920
# bygg ... sedan kontrollbilder (6–20 tidpunkter räcker):
bash .claude/skills/bang-motion/scripts/run.sh snap   work/bang-motion/<projekt> work/bang-motion/<projekt>/shots 1 3.5 8 12
# full export (bildruta för bildruta, ingen tappad bildruta):
bash .claude/skills/bang-motion/scripts/run.sh export work/bang-motion/<projekt> 30      # -> out.mp4
```

- `run.sh` installerar `puppeteer-core` lokalt i `work/bang-motion/_tools` första gången och använder installerade Chrome
  (`CHROME_PATH` för annan sökväg). Inget globalt.
- Sidan måste exponera `window.OPENER = { W, H, DURATION, tl, ready, seek(t) }` – alla startfiler gör det.
  `?clean=1` stoppar autoplay (export), `?debug=1` ger en scrubbar.
- Efter exporten: avkoda MP4:an (`ffmpeg -v error -i out.mp4 -f null -`), gör kontaktark och titta. Lägg på ljud och
  Spotlight-slutbild. Ska filmen leva vidare som projekt: flytta till `work/<mapp>/` enligt `/film`.
- Fungerande exempel i 9:16 med Golfkupongers typsnitt, logga och banfoto: `assets/exempel-gk-9x16.html`
  (tekniktest – kamera + kinetisk rubrik + riktad rörelseoskärpa; inte en färdig annons).

## Startfiler (`assets/`)

| Fil | Stil | För |
|---|---|---|
| `starter-opener.html` | Opener med Three.js-bakgrund, kamerarigg, textanimationer (`inUp`, `inMask`, `inWords`, `typeOn` …), ljusläckor, push-through | promos, openers, kinetisk typografi |
| `starter-explainer.html` | Kontinuerlig handling – ett subjekt som aldrig stannar | processer, rutter, hastighet |
| `starter-explainer-kartun.html` | Tecknat kollage – krämpapper, urklipp, handskrift | utbildning, vetenskap |
| `starter-explainer-jurnalisme.html` | Visuell journalistik – svart, riktiga foton med källtagg, överstrykningspenna | nyheter, aktuellt |
| `starter-explainer-katalog.html` | Vit katalog – vitt rutnät, produkturklipp | produkter, varumärken |
| `starter-explainer-sketsa.html` | Vintage-skiss – sepiapapper, gravyrer, serif | historia, biografi |
| `starter-explainer-panggung.html` | Tecknad scen – en scen per avsnitt, ledade figurer, ingen text | utbildning med figurer |

Startfilerna har platshållare `GANTI:` (= "byt ut"). Stilen ska härledas ur varumärket – ärv inte startfilens look.

## Referenser (`references/`, indonesiska)

| Fil | Innehåll |
|---|---|
| `ORIGINAL-SKILL.md` | Hela originalskillen: PPT-testet, fyra lagar, stilriktningar, arbetsflöde, checklista, fallgropar |
| `anti-ppt.md` | Varför agenter faller i slide-mönster, tabell fel → rättelse, kalibrering |
| `opener-konsep.md` | 19 öppningskoncept, menyer för öppning (3 första s), övergångar, avslut, feature-presentation |
| `techniques.md` | Levande typografi, riktad oskärpa, kamera/shot-storlekar, övergångar, ljusläckor, glow, Three.js-bakgrunder, bakgrundsrörelse, grainy gradient, UI-mockups, video som lager |
| `explainer.md` | Explainerflöde, scenbyggnad (3–5 element per scen), mobil läsbarhet, VO-synk, sociala format |
| `kartun-panggung.md` | Tecknad scen: 7 lagar, ledrigg, huvuden |
| `architecture.md` | Filstruktur, scen 1920×1080 skalad, kamerarigg `#world`, determinism, export |
| `roadmap.md` | Upphovspersonens prioriteringar och antimönster |

Ordlista: *adegan* = scen, *kamera* = kamera, *latar* = bakgrund, *teks hidup* = levande text, *judul* = rubrik,
*panggung* = scen/scenografi, *ganti* = byt ut, *larangan* = förbud, *hukum* = lag, *cek* = kontroll.

## Borttaget vid importen

After Effects-bryggan via Higgsfield MCP (`references/ae-bridge-higgsfield.md`, `scripts/ae/`) – kräver AE och betaltjänst.
Avsnittet `## After Effects` i `ORIGINAL-SKILL.md` gäller alltså inte här.
