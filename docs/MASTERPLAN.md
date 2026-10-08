# Content Engine – masterplan

> Levande dokument. Skrivet för att människor **och andra AI:er** ska kunna följa, ifrågasätta och förbättra
> det. Varje större beslut har ett *varför* och valda bort-alternativ. Hittar du ett bättre sätt: skriv det i
> **§9 Utmana planen** med motivering, och uppdatera beslutsloggen när det är avgjort.
>
> Senast uppdaterad: 2026-10-09 · Ägare: Jonas (+ kollega) · Underlag: intervju 2026-10-09, kodgranskning av `main` @ 8b101bc.

---

## 1. Slutmål (ägarens egna ord, sammanfattat)

**En automatisk marknadsavdelning i molnet** för flera bolag – främst **Golfkuponger** (golfkuponger på 300+
svenska klubbar; friskvårdsbidrag, företagspaket, presentkort) och **FAIV** (grill-kit till bilar och
extrabelysning till bilar). Två användare: Jonas och en kollega.

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
           GODKÄNN I MOBILEN (Telegram först; tumme + kommentar → omarbetning)
                                           ▼
           PUBLICERA (Postiz schema) · ANNONS (Meta Marketing API, senare)
                                           ▼
           MÄTA (Postiz/Meta) → LÄRA (ML + ägarens tummar) → INSYN (UI: gjort/lärt/hett)
                                           └──────────────► tillbaka till BESLUTA
```

## 5. Beslut (med varför och bortvalda alternativ)

| # | Beslut | Varför | Bortvalt (och varför) |
|---|---|---|---|
| D1 | **Viral discovery via Apify** (TikTok-, Instagram-hashtag-/explore- och profilscrapers) i stället för Virlo. | Ägaren har ingen Virlo-nyckel; Apify är redan integrerat, betalas per körning med kostnadstak, täcker TikTok. | Virlo (behåller koden, aktiveras om nyckel finns). Egen scraping utan Apify (skör, ToS-risk). |
| D2 | **Mobilgodkännande via Telegram-bot först**, PWA i appen senare. | Gratis, notis direkt, spelar video inline, knappar 👍👎 + svar som kommentar, noll appinstallation. | Webb-push/PWA (mer bygge, iOS-begränsningar). E-post (långsamt, ingen inline-video). SMS (kostar, ingen video). |
| D3 | **Molnrendering med HyperFrames i en container-worker** (Render Background Worker eller Google Cloud Run-jobb), Remotion-workern behålls för befintliga mallar. | HyperFrames är Apache-2.0, kör i headless Chrome + ffmpeg, har inbyggt `cloudrun`/`lambda`-stöd; hela `library/` är HyperFrames. Cloud Run skalar till noll (betalar per rendering). | Bara Remotion (kräver företagslicens för större bolag, katalogen låst). Lokala datorn (bryter "molnet"-målet). |
| D4 | **Riktig rörlig film = egen bank + AI-video.** Egen media taggas i mediabanken; luckor fylls med AI-video (Kling/Seedance via Higgsfield, ev. Veo) med kostnadsgrind. | Ägarens #1: "riktig filmad video". AI-video för scener vi saknar (t.ex. grill vid bil i solnedgång). | Bara stillbilder + grafik (underkänt av ägaren). Stockvideo (generiskt, licenskrångel). |
| D5 | **Vision-modell förstår referenser och granskar vår output** (ramar ur videon → beskrivning, poäng). | Text-analys av bildtext missar varför en video fungerar; samma modell kan vara kvalitetsgrind. | Bara bildtext (dagens läge). Människa granskar allt (skalar inte). |
| D6 | **Lärande i två lager:** (a) snabbt – ägarens tummar + kommentarer och tidiga resultat styr prompts/val direkt; (b) långsamt – ML-modell när data räcker, med media- och krokfeatures. | 80-etikettsgränsen tar månader; ägarens bedömning finns från dag 1 och är högkvalitativ. | Vänta på ML (för långsamt). Sänka gränsen hårt (överanpassning). |
| D7 | **Säsong/kalender som egen källa** (svenska högtider, friskvård "brinner inne" Q4, golfsäsong, grillsäsong, mörkerperiod för extraljus). | Starka, förutsägbara köptillfällen för båda bolagen. | Bara trender (missar planerbara toppar). |
| D8 | **Render: uppgradera webbtjänsten till betald (starter)** när automatiken går live. | Gratisplanen somnar och har tappat formulär; Telegram-webhooks och schema kräver att appen är vaken. | Behålla free (opålitligt). |
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

### Fas 2 – Toppkvalitet på video (ägarens prio 1)
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
- Telegram-bot (D2): video + text + knappar 👍 / 👎 / ✏️; svar = kommentar → omarbetning → ny version.
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
5. Telegram ok som första mobilkanal?

## 9. Utmana planen

*Skriv här: vad du (människa eller AI) tycker är fel, saknas eller kan göras bättre – med motivering och
gärna förslag. Datera och signera.*

-

## 10. Beslutslogg

| Datum | Beslut | Av |
|---|---|---|
| 2026-10-09 | Masterplan v1 (D1–D9, faser 0–7) | Claude + Jonas (intervju) |
| 2026-10-07 | Stilregler blir råd, inte spärrar (AdBrief advisories); fakta spärrar fortfarande | Jonas |
| 2026-10-08 | Content Library + /studio mergat (PR #85) | Jonas |
