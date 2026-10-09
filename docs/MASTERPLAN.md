# Content Engine – masterplan

> Levande dokument. Skrivet för att människor **och andra AI:er** ska kunna följa, ifrågasätta och förbättra
> det. Varje större beslut har ett *varför* och valda bort-alternativ. Hittar du ett bättre sätt: skriv det i
> **§9 Utmana planen** med motivering, och uppdatera beslutsloggen när det är avgjort.
>
> Senast uppdaterad: 2026-10-09 · Ägare: Jonas (+ kollega) · Underlag: intervju 2026-10-09, kodgranskning av `main` @ 8b101bc.

---

## 1. Slutmål (ägarens egna ord, sammanfattat)

**En automatisk marknadsavdelning i molnet** för flera bolag – främst **Golfkuponger** (golfkuponger på 300+
svenska klubbar; friskvårdsbidrag, företagspaket, presentkort) och **FAIV** (Fordonsanpassning i Väst AB, Kungälv: extraljus, LED-ramper, fordonsspecifika
**grillkit** = ljus integrerat i bilens frontgrill, arbetsljus, husbilsel, arbetsfordon – jämförbara: Ekstralys,
Extraljuskungen, Ljusgiganten, vparts, Strands). Två användare: Jonas och en kollega.

1. **Bevakar** konton (konkurrenter, inspiration, kreatörer), Meta Ads Library (vilka annonser som körs och hur
   länge – länge = fungerar) och viralt innehåll – i branschen, i närliggande branscher och breda virala format.
2. **Gör vår spinn direkt** när något är riktigt bra för oss: samma grammatik (krok, format, rytm), vår vinkel,
   våra verifierade fakta, vårt material. Aldrig kopior.
3. **Egna idéer** från egna resultat, säsong/kalender och trender – och från en mening till ChatGPT/Claude.
4. **Toppkvalitet**: riktig rörlig film (egen eller AI-genererad) + proffsig redigering + stark krok. 5–7 inlägg
   per bolag och vecka, organiskt och Meta-annonser. Instagram + Facebook nu, TikTok senare.
5. **Godkänns med en tumme i mobilen** (+ kort kommentar som ändrar) → publiceras eller schemaläggs via Postiz.
6. **Lär sig av resultaten** (ML) – och **visar allt** för ägaren: vad den gjort, vad den lärt sig, vilka inlägg
   som är heta, vilka konton/annonser som går bäst. *"Två hjärnor är bättre än en."*
7. **Kör i molnet**, inte beroende av en dator.
8. **Budget**: gratis där det går; betalt när kvaliteten blir tydligt bättre; kvalitet först när skillnaden är stor.

**Vad ägaren uttryckligen INTE vill ha**: generiskt "AI-mall"-innehåll – stillbilder med grafik, PowerPoint-/webbkänsla,
billiga effekter (blixtar, glow, guldsfär, 3D-text), förutsägbart tempo. Inga stilregler som spärrar kreativitet.

## 2. Nuläge (2026-10-09)

| Del | Status | Kärnproblem |
|---|---|---|
| Bolag | Golfkuponger, FAIV och Sänk Dig Golf finns i prod. Bara Sänk Dig har Postiz och fakta. | FAIV saknar brand, fakta, skills, mallar. Ad Studio/Motion är hårdkodade till Golfkuponger. |
| Bevakning konton | Instagram via Apify, dagligen, 10 senaste inläggen per konto. | AI-analysen fallerar (OpenRouter-nyckel saknas i jobbet). Bara Instagram, likes+kommentarer (inte visningar), läser bildtext – inte video. |
| Meta Ads Library | Apify `eiv/meta-ads-library-scraper`, sparar start/slut/aktiv. | Ingen ranking på livslängd, text-analys bara, ett konto, "begränsad täckning". |
| Viral discovery | Virlo-integration byggd. | Avstängd – ingen nyckel (ägaren har ingen). |
| Dagligt jobb | GitHub Actions 06:17 UTC, påslaget. | Kraschar 1/10, 7/10, 8/10 på `migrate --check`. |
| Idé → inlägg | Fungerar manuellt (knapp/MCP → 3 idéer → copy). | **Ingenting startar automatiskt.** Ingen veckoplan, ingen säsongslogik. |
| Video | Creative Engine (OpenAI-bild, Higgsfield Kling/Seedance), Motion Engine (Remotion), Content Library (HyperFrames, lokalt). | **Ingen färdig redigerad video renderas i molnet.** Remotion kör bara på lokal Windows-worker. Higgsfield 401 i senaste kontroll. Ingen kvalitetskontroll av genererad media. |
| Godkännande | Webbformulär per objekt. | Ingen kö, ingen tumme, inga notiser. |
| Publicering | Postiz-utkast fungerar (Sänk Dig). Schemaläggning bara via MCP. | Ingen autoschemaläggning, ingen Meta Ads API, ingen TikTok. |
| ML | Ridge-modell, shadow, promotion. | Har aldrig tränat (≥80 etiketter krävs). Bara idé-flödet skapar etiketter. Inga media-/krokfeatures. |
| Insyn | Lista egna inlägg (datumsorterad), hopfälld lärräknare. | Ingen "heta inlägg"-ranking, ingen berättelse om vad den gjort/lärt sig, ingen kalender. |
| Drift | Render free (somnar), GitHub Actions för schema. | Kallstart ~70 s, har tappat formulär. |

Detaljer: kodgranskningen i sessionens underlag; relevanta filer listas per fas nedan.

## 3. Principer (och varför)

1. **Börja aldrig från noll.** Allt innehåll utgår från en verifierad referens eller mall (`library/`, bevakade
   vinnare). *Varför:* modeller utan referens faller tillbaka till genomsnittligt "AI-utseende".
2. **Grammatik, inte innehåll.** Vi lånar krok, format, rytm, kameraspråk – aldrig andras text, bild, varumärke.
   *Varför:* juridiskt säkert och ger vår egen identitet.
3. **Rörlig film först, grafik som finish.** *Varför:* ägarens dom över v2 – stillbilder + effekter läses som billigt.
4. **Människan bestämmer, maskinen föreslår.** Inget publiceras utan en tumme tills ägaren själv slår på auto för
   en viss typ. *Varför:* varumärkesrisk; och ägarens bedömning är träningsdata.
5. **Allt mäts och förklaras.** Varje automatiskt beslut loggas med skäl som visas i UI. *Varför:* "två hjärnor"
   – ägaren ska kunna lära sig av systemet och rätta det.
6. **Fakta är det enda som spärrar.** Stil är fri; påståenden i reklam måste vara verifierade i faktabanken.
7. **Billigt först, betala för kvalitet som syns.** Varje betald tjänst har kostnadstak och visas i `/costs/`.
8. **Molnet är målet, lokalt är labbet.** Claude Code + `library/` är verkstaden där nya mallar/effekter tas fram
   och verifieras; det som fungerar flyttas till molnpipeline.

## 4. Målarkitektur

```
           ┌──────────── BEVAKNING (dagligen → senare flera gånger/dag) ─────────────┐
           │ Konton (IG, FB, TikTok) · Meta Ads Library (livslängd) · Viral discovery │
           │ (i branschen / närliggande / breda format) · egna resultat · kalender   │
           └───────────────────────────────┬─────────────────────────────────────────┘
                                           ▼
                         SIGNALER  (visningar, momentum, livslängd, relevans)
                                           ▼
                 FÖRSTÅ  (vision-modell tittar på videon: krok, format, rytm, varför)
                                           ▼
                 BESLUTA  (är det bra för oss? → vinkel + fakta + vilken mall)
                                           ▼
     PRODUCERA  copy · bilder · klipp (egna / AI-video) → REDIGERA (molnrendering, beat, grafik)
                                           ▼
                 KVALITETSGRIND  (vision-kritik: poäng ≥ 8 annars om)
                                           ▼
           GODKÄNN I MOBILEN (Discord; 👍/👎, Ändra, Kommentar, betyg 1–10 → lärdomar)
                                           ▼
           PUBLICERA (Postiz schema) · ANNONS (Meta Marketing API, senare)
                                           ▼
           MÄTA (Postiz/Meta) → LÄRA (ML + ägarens tummar) → INSYN (UI: gjort/lärt/hett)
                                           └──────────────► tillbaka till BESLUTA
```

## 4b. Produktionsmotorn – referens → recept → modell per scen → klipp

*Ägarens vision (2026-10-09):* bevakningen hittar inlägg/annonser vi bör göra. Biblioteket har skills, mallar och
exempelpromptar **per videotyp och per modell**, så att Claude/ChatGPT kan bygga en film lika bra som referensen –
fast med vår spinn. Exempel: en verklig människa vid en Volvo som visar FAIV:s nya grillkit – då ska allt finnas för
att göra människan perfekt, produkten exakt och allt runt omkring optimalt för respektive modell.

```
Referens (bevakad annons/inlägg, eller egen idé)
   │  1. NEDBRYTNING – vision-modell: scener, tider, kamera, ljus, krok, klipprytm, ljud, varför det fungerar
   ▼
Produktionsrecept (library: recipes/<typ>)  e.g. "person-presenterar-produkt-vid-bil", "mörker→ljus-reveal",
   │                                              "gatuintervju", "sketch-med-återkommande-karaktär", "UGC-tips"
   │  2. SHOTLIST med vår spinn: vinkel, fakta (faktabanken), varumärke (brand-kit), material (mediabank)
   ▼
   3. MODELLVAL PER SCEN (model playbooks i library: models/<modell>)
      • karaktär/människa  → konsekvent karaktär (referensbild-ark) + bästa människomodell (t.ex. Seedance)
      • tal/läppsynk       → modell med native ljud/läppsynk (t.ex. Veo 3.1) eller röst (ElevenLabs/egen) + lipsync
      • produkt i rörelse   → Kling/Seedance med första/sista bild från exakt produktfoto (aldrig påhittad produkt)
      • miljö/b-roll       → billigaste modell som klarar scenen
      • effekter/grafik    → HyperFrames-library (kod, gratis)
      • bild/förstarutor   → gpt-image-2 (komposit: person + bil + riktig produkt)
   │  4. PROMPT PER MODELL – modellens eget format, parametrar, kända fallgropar, verifierade exempel
   ▼
   5. GENERERA (kostnadsgrind, preflight-estimat) → 6. VISION-QA per klipp (händer, ansikte, produkt exakt?)
   ▼
   7. KLIPP & FINISH (HyperFrames i molnet): beat, kamerarörelser, typografi, grade, ljud/SFX, −14 LUFS
   ▼
   8. KRITIKLOOP mot referensen (poäng ≥ 8) → mobilgodkännande → publicering → lärande per recept & modell
```

**Biblioteket utökas med två nya typer** (utöver mallar/effekter/prompts):
- `library/models/<modell>/PLAYBOOK.md` – styrkor/svagheter, promptformat, parametrar, pris, fallgropar
  (händer, text, produktlogotyper), 3–5 verifierade exempel med prompt + resultat. Källa för `creative_director`.
- `library/recipes/<typ>/RECIPE.md` + `recipe.json` – scenstruktur, modellval per scen, promptmallar, klipp-mall
  (HyperFrames), ljudmall, QA-checklista och referensexempel. Varje recept testas och märks verified.

| # | Beslut | Varför | Bortvalt |
|---|---|---|---|
| D10 | **Modellval per scen, inte per film** – routning efter scentyp via model playbooks; modellregistret (`engine/creative_registry.py`) är sanningen om vad som är tillgängligt/verifierat. | Ingen modell vinner allt (Seedance människor/produkt, Veo läppsynk/dialog, Kling produktrörelse/längre klipp). | En modell för allt (sämre per scen). |
| D11 | **Recept är den återanvändbara enheten** – varje lyckad film blir ett recept med promptar, modellval och klipp-mall som nästa film startar från; lärandet mäter per recept och modell. | "Börja aldrig från noll" i praktiken; jämförbart och förbättringsbart. | Fri prompt varje gång (inkonsekvent, går inte att lära av). |
| D12 | **Exakt produkt, genererad omgivning** – produkter (grillkit, logotyper, appskärmar) kommer från riktiga foton/inspelningar som första/sista bild eller komposit; AI genererar människa, miljö och rörelse. | AI hittar på produktdetaljer; varumärkesrisk. | Låta modellen rita produkten. |

**Pilot (först):** två recept, ett per bolag, byggda och verifierade end-to-end:
1. FAIV – "person vid bil visar grillkit, mörker→ljus" (ref: Xenonkungen "Monterat & Klart", Ljusgiganten POV, Ultra Vision grillkit-reveal).
2. Golfkuponger – "återkommande karaktär / sketch om friskvårdsbidraget" (ref: Timeplan, Melkers julkalender, Duolingo-påminnelse).

## 5. Beslut (med varför och bortvalda alternativ)

| # | Beslut | Varför | Bortvalt (och varför) |
|---|---|---|---|
| D1 | **Viral discovery via Apify** (TikTok-, Instagram-hashtag-/explore- och profilscrapers) i stället för Virlo. | Ägaren har ingen Virlo-nyckel; Apify är redan integrerat, betalas per körning med kostnadstak, täcker TikTok. | Virlo (behåller koden, aktiveras om nyckel finns). Egen scraping utan Apify (skör, ToS-risk). |
| D2 | **Mobilgodkännande i Discord via ägarens befintliga n8n-bot** (samma bot och knapp-endpoint som AI Radar). Video bifogas (länk om > uppladdningsgränsen); 👍/👎, ✏️ Ändra, 💬 Kommentar, betyg 1–10. Kommentarer tolkas mot videons manifest → lärdomar per biblioteksobjekt/aspekt. | Ägaren använder redan Discord för ChatGPT-flöden; en kanal för allt; bot-token stannar i n8n; n8n svarar Discord direkt så Render-kallstart inte bryter 3-sekundersgränsen. | Telegram (ägaren valde bort, 2026-10-09). Egen Discord-app direkt mot Render (kallstart > 3 s). PWA (mer bygge). |
| D3 | **Molnrendering med HyperFrames i en container-worker** (Render Background Worker eller Google Cloud Run-jobb), Remotion-workern behålls för befintliga mallar. | HyperFrames är Apache-2.0, kör i headless Chrome + ffmpeg, har inbyggt `cloudrun`/`lambda`-stöd; hela `library/` är HyperFrames. Cloud Run skalar till noll (betalar per rendering). | Bara Remotion (kräver företagslicens för större bolag, katalogen låst). Lokala datorn (bryter "molnet"-målet). |
| D4 | **Riktig rörlig film = egen bank + AI-video.** Egen media taggas i mediabanken; luckor fylls med AI-video (Kling/Seedance via Higgsfield, ev. Veo) med kostnadsgrind. | Ägarens #1: "riktig filmad video". AI-video för scener vi saknar (t.ex. grill vid bil i solnedgång). | Bara stillbilder + grafik (underkänt av ägaren). Stockvideo (generiskt, licenskrångel). |
| D5 | **Vision-modell förstår referenser och granskar vår output** (ramar ur videon → beskrivning, poäng). | Text-analys av bildtext missar varför en video fungerar; samma modell kan vara kvalitetsgrind. | Bara bildtext (dagens läge). Människa granskar allt (skalar inte). |
| D6 | **Lärande i två lager:** (a) snabbt – ägarens tummar + kommentarer och tidiga resultat styr prompts/val direkt; (b) långsamt – ML-modell när data räcker, med media- och krokfeatures. | 80-etikettsgränsen tar månader; ägarens bedömning finns från dag 1 och är högkvalitativ. | Vänta på ML (för långsamt). Sänka gränsen hårt (överanpassning). |
| D7 | **Säsong/kalender som egen källa** (svenska högtider, friskvård "brinner inne" Q4, golfsäsong, mörkerperiod för extraljus, husbilssäsong). | Starka, förutsägbara köptillfällen för båda bolagen. | Bara trender (missar planerbara toppar). |
| D8 | **Render: uppgradera webbtjänsten till betald (starter)** när automatiken går live. | Gratisplanen somnar och har tappat formulär; schema och snabba svar på Discord-feedback kräver att appen är vaken. | Behålla free (opålitligt). |
| D9 | **FAIV får eget brand-/fakta-/skillpaket** och mallar generaliseras per bolag (inget hårdkodat Golfkuponger). | Två bolag med helt olika målgrupp och ton. | Dela Golfkupongers (fel ton/fakta). |

## 6. Faser (ordning, innehåll, klart-kriterier)

Varje fas levereras som PR mot `main` med tester och en kort "vad ändrades / hur verifierat" i PR-texten.

### Fas 0 – Laga grunden (nu)
- Dagliga jobbet: diagnos av saknade migreringar, `OPENROUTER_API_KEY` och `HIGGSFIELD_API_KEY_GK` in i workflow.
- Rensa stale docs (README säger att daily är av).
- **Klart när:** dagligt jobb grönt två dagar i rad; konkurrentanalys utan OpenRouter-fel.
- **Ägaren behöver:** lägga `CONTENT_OPENROUTER_KEY` i GitHub Secrets; kolla Render-deploy för 6/10–8/10.

### Fas 1 – Bolagen på riktigt
- Generalisera Ad Studio/Motion brand från hårdkodat till per bolag (`Company` + brand-kit: färger, typsnitt, logga, ton).
- FAIV: brand-skill, faktabank, målgrupp, säsonger, startbevakning (konton + annonssidor).
- Postiz-koppling för Golfkuponger och FAIV (ägaren skapar Postiz-konto/kanaler).
- **Klart när:** båda bolagen har profil, fakta, brand-kit, ≥10 bevakade konton, ≥5 bevakade annonssidor, Postiz-kanaler.

### Fas 2 – Toppkvalitet på video (ägarens prio 1) – se §4b produktionsmotorn
- Referensbibliotek: 10–12 godkända referensannonser (pågår) → strukturerad "grammatik" per referens.
- Videopipeline: shotlist från referens → klipp (egen bank / AI-video) → redigering i HyperFrames (beat, kamera,
  typografi som finish) → vision-kritik → render.
- Molnrendering (D3) med kostnadstak.
- **Klart när:** ägaren bedömer 3 av 3 testfilmer per bolag som "publicerbara utan att skämmas"; rendering i molnet utan dator.

### Fas 3 – Bevakning → vår spinn
- Konton: visningar i signalen, fler poster än 10 senaste, oftare än dagligen för heta konton, TikTok.
- Meta Ads: livslängdsranking ("aktiv i X dagar"), varianter, videoanalys.
- Viral discovery (D1) i tre ringar: bransch → närliggande → breda format; relevansfilter per bolag.
- Vision-förståelse (D5) av topp-poster/-annonser.
- Automatisk trigger: över tröskel → ContentRun + utkast till kreativ (Fas 2-pipeline) → godkännandekö.
- **Klart när:** varje vecka dyker ≥3 "vår spinn"-förslag per bolag upp automatiskt med länk till originalet och förklaring.

### Fas 4 – Mobilgodkännande och publicering
- Discord (D2, `engine/review/`): video + text + 👍 / 👎 / ✏️ Ändra / 💬 Kommentar / 1–10. Varje video har ett manifest
  (scener, tider, exakta biblioteks-id:n) så att "effekten vid 0:07 är billig" hittar rätt effekt. Kommentaren tolkas
  till lärdomar (undvik / mer av / justera, med styrka) som rankar biblioteket och följer med varje nytt utkast.
  Ändra → ny version postas i samma kanal. Betyg 1–10 blir etiketter för lärandet.
- Godkänt → Postiz-schema i nästa lediga slot (veckoplan 5–7 per bolag).
- **Klart när:** ägaren kan gå igenom en veckas förslag i mobilen på < 10 minuter; inget publiceras utan tumme.

### Fas 5 – Autonom veckoplan
- `run_daily` får produktionssteg: veckoplan per bolag (mix: spinn, säsong, egna idéer, annons), kvoter, kostnadstak.
- Säsong/kalender (D7).
- **Klart när:** varje måndag ligger 5–7 färdiga förslag per bolag i godkännandekön utan att någon tryckt på något.

### Fas 6 – Lärande och insyn ("två hjärnor")
- Snabba lagret (D6a): tummar/kommentarer + tidiga resultat → preferenser som styr idé-, mall- och klippval.
- Långsamma lagret (D6b): fler etikettkällor (alla flöden), media-/krok-/format-/tid-/säsongsfeatures.
- Insyns-UI: **Heta inlägg** (egna + bevakade, rankade), **Vad systemet gjort** (logg med skäl), **Vad det lärt sig**
  (veckorapport på svenska + vinnande mekanismer/format), **Kalender** (planerat vs publicerat), annonslivslängd.
- **Klart när:** ägaren kan svara "vad fungerar för oss just nu och varför" genom att öppna en sida.

### Fas 7 – Annonser hela vägen + TikTok
- Meta Marketing API: skapa kampanj/annonsuppsättning/annons från godkänd kreativ, budgetgränser, auto-hämtning av
  resultat (CTR/CPA/ROAS) in i lärandet.
- TikTok-publicering via Postiz.
- **Klart när:** en godkänd annons går live med en tumme och dess resultat syns i insyn efter 24 h.

## 7. Risker

| Risk | Motåtgärd |
|---|---|
| AI-video ser "AI" ut | Referensstyrd shotlist, vision-grind, egen media först, ägarens tumme. |
| Kostnader skenar (Apify, AI-video, rendering) | Kostnadstak per bolag/dag, preflight-estimat, `/costs/`, inget betalt utan grind. |
| Plattforms-ToS/scraping | Bara publika data via Apify-aktörer; inga inloggade scrapers; inga kopior av innehåll. |
| Felaktiga påståenden i reklam | Faktabanken spärrar overifierade påståenden. |
| Windows-lokala verktyg (Smart App Control) | Allt produktivt flyttas till moln-containrar (Linux). |
| Render free somnar | D8. |

## 8. Öppna frågor till ägaren

1. Postiz: skapa konton/kanaler för Golfkuponger och FAIV (trial nu) – vilken plan?
2. Budget per bolag och månad för Apify, AI-video och molnrendering (förslag: start 300–500 kr/bolag/mån, höj när kvaliteten bevisats).
3. Egen media: finns klipp/foton från banor (Golfkuponger) och bilar/grill/ljus (FAIV)? Var ska de laddas upp?
4. Vilka konton och annonssidor ska bevakas från start per bolag (vi föreslår en lista att godkänna)?
5. ~~Telegram ok som första mobilkanal?~~ Nej: Discord via befintlig n8n-bot (beslutat 2026-10-09).

## 9. Utmana planen

*Skriv här: vad du (människa eller AI) tycker är fel, saknas eller kan göras bättre – med motivering och
gärna förslag. Datera och signera.*

-

## 10. Beslutslogg

| Datum | Beslut | Av |
|---|---|---|
| 2026-10-09 | Masterplan v1 (D1–D9, faser 0–7) | Claude + Jonas (intervju) |
| 2026-10-09 | Produktionsmotorn: modell per scen, recept, exakt produkt (D10–D12), pilot ett recept per bolag | Jonas + Claude |
| 2026-10-09 | Analys: gratis → GLM 5.3 Flash → Gemini 3.1 Flash-Lite, även annonser | Jonas |
| 2026-10-09 | Produktkatalog: alla produkter + banor från hemsidan, bara URL:er; bilder laddas ner när de används | Jonas |
| 2026-10-09 | Godkännande i Discord (inte Telegram) via befintlig n8n-bot; betyg 1–10 + kommentarer → lärdomar per effekt/mall | Jonas |
| 2026-10-07 | Stilregler blir råd, inte spärrar (AdBrief advisories); fakta spärrar fortfarande | Jonas |
| 2026-10-08 | Content Library + /studio mergat (PR #85) | Jonas |
