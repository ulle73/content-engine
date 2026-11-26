---
name: referens
description: Från en känd, etablerad företagsfilm till vår egen version – hitta förslag, låt Jonas välja, hämta, bryt ner klipp för klipp med rea-video (hur varje klipp är gjort, berättelsen, tempo, text och ljud), gör referensens berättelse till ett storyboard-ark och skriv om det till Golfkupongers innehåll. Använd ALLTID när Jonas ber om kända/etablerade företagsvideor, inspiration eller referenser, skickar en videolänk han gillar, eller säger "gör en sån här".
---

# Referensfilm → vår film

Beslut Jonas 2026-11-26: när han ber om kända företagsfilmer används det här arbetssättet som standard. Vi lånar
**hur** filmen är byggd (berättelse, tempo, övergångar, ljudgrepp), aldrig dess bilder, personer, formuleringar,
musik, varumärke eller påståenden (samma regel som `skills/teknik`).

## 1. Hitta – förslag, inget laddas ner

När Jonas ber om kända/etablerade företagsfilmer eller inspiration:
- **Bevakade konkurrenter:** MCP `list_reference_candidates` (annonser som gått längst och nått flest i EU först).
- **Kända varumärken** (Spotify, Airbnb, ClassPass, Apple, Strava …): sök i Metas annonsbibliotek (meta-ads-MCP
  `ads_library_search`, bara läsning), YouTube och Instagram. Leta efter samma *problem* som vårt (förklara en tjänst,
  en app-lansering, "så funkar det", ett erbjudande med deadline) – inte samma bransch.
- Visa **5–8 kort**: länk, varumärke, längd, format, en mening om greppet (krok/struktur) och varför det passar
  Golfkuponger. Jonas väljer en (eller skickar en egen länk).

## 2. Hämta

```bash
.venv/Scripts/python.exe -I library/techniques/hamta.py "<länk>"     # → work/references/<slug>/video.mp4 + meta.json
```
Kräver sajten inloggning: be Jonas ladda ner filen och lägg den som `work/references/<slug>/video.mp4`.

## 3. Bryt ner med rea-video

rea-video (github.com/JuneYaooo/rea-video, Apache-2.0) är installerat lokalt i `work/_verktyg/rea-video/.venv`.
Saknas det: `cd work/_verktyg && git clone --depth 1 https://github.com/JuneYaooo/rea-video && cd rea-video &&
py -3.12 -m venv .venv && .venv/Scripts/python.exe -m pip install ".[ocr]"` och sedan
`.venv/Scripts/python.exe -m pip uninstall -y opencv-python && .venv/Scripts/python.exe -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"`.

```bash
cd work/references/<slug>
export PYTHONIOENCODING=utf-8 REA_VIDEO_LANG=en; R=../../_verktyg/rea-video/.venv/Scripts/rea-video.exe
$R decompose video.mp4 -o rea --lang en          # ~2 min för 30 s, helt lokalt, inget skickas någonstans
$R review rea                                    # skriver rea/review_tasks.json + rea/review_answers.json
```

**Granskningen är obligatorisk.** Utan den gissar verktyget ofta fel på plattformsomkodade filmer (ClassPass-testet
2026-11-26: verkliga klipp blev "AI-video"). Titta på `rea/storyboard.jpg` och `rea/shots/shot_XXX.jpg`, och fyll i
`review_answers.json` per klipp: `label_probs` (live_action, code_render, screen_capture, ai_video, cg_3d, anim_2d,
still_motion …), `description`, `narrative` {`role`: hook/context/info/proof/turn/payoff/cta/mood, `point`: vad
klippet säger} och överst `story` {summary, hook, highlights}. Sedan:

```bash
$R apply-review rea --by Claude && $R summary rea/breakdown.json
```

Läs bara `rea/VIDEO.md` (~2k tokens) och vid behov `rea/video/{timeline,content,rhythm,sound,packaging}.md` –
aldrig `breakdown.json` eller `report.md`. Fullständig dokumentation: `work/_verktyg/rea-video/skills/rea-video/SKILL.md`.

**Använd inte** rea-videos återskapningsdel (`remake`, `remake-run`, capsule-cinema, ChatCut): den kostar och kopierar
referensen. Inte heller `reverse-any-video` (HyperFrames Pro, bildruta-för-bildruta-kopia).

## 4. Referensens storyboard

```bash
.venv/Scripts/python.exe scripts/storyboard.py work/references/<slug> --fran-rea work/references/<slug>/rea
```
→ `storyboard-referens.json` + `out/storyboard-referens.png`: ett kort per berättelsesteg (Krok, Bakgrund, Bevis,
Vändning, Uppmaning …) med referensens bild, poäng, vad som syns och övergången till nästa. Visa arket för Jonas
tillsammans med 3–5 rader: berättelsen, tempot (klipp per minut, scenlängder ur `video/rhythm.md`), text- och
ljudgreppen och vilka tekniker vi tar.

## 5. Vår version

1. Spara greppen i teknikbanken (`skills/teknik` B, en post per distinkt teknik, referenslänken som bevis).
2. Starta filmen i `work/<ny-film>/` (ny mapp eller `../_verktyg/ny-film.sh` från närmaste egna film) och kopiera
   referensens storyboard in som `"storyboard"` i `film.json`. Ta bort `"referensutkast"` och skriv om **varje scen**:
   samma uppgift i berättelsen, vårt innehåll – riktiga banfoton, Tourleif/Chefen, appen, fakta ur faktabanken,
   Golfkupongers Spotlight-slutbild sist, 9:16. Fyll `rorelse`, `blir`, `ljud` och `text` (läsregeln kontrolleras).
3. Fortsätt i `skills/studio` + `skills/video-regler` avsnitt 2: storyboard-arket är beslutsrundan; `./make.sh bild`
   spärras tills det är godkänt.
