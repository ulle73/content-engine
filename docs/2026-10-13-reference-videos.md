# Referensvideor → vår version

**Mål:** bevakningen (annonser och konton vi följer) eller en länk som någon klistrar in blir underlag för en egen,
bättre film för FAIV eller Golfkuponger. Samma flöde för ChatGPT (MCP) och Claude (MCP eller `reference_lab`).

```
länk / bevakad annons
  → hämta (yt-dlp: Meta Ad Library, Instagram, TikTok, YouTube, Facebook; eller direktlänk) → egen kopia i R2
  → mät (PyAV, gratis): klipp (bildruteexakta), mjuka övergångar, rörelse per scen, tempo, tystnad, ljudnivå
     + liten proxy (≤ 720 px) + kontaktkarta (en bild per scen)
  → bryt ner (Gemini tittar och lyssnar på proxyn, med mätningarna som ankare): scen för scen med tider, krok,
     struktur, kamera, text, tal, musik, ljud, tempo, varför den fungerar, vad som inte får kopieras
  → vår version: bolagets brand, verifierade fakta, mediabank, produkter, recept och model playbooks → scenplan
     med material per scen (asset_id / produktbild / filma / AI-scen), fakta att verifiera, inspelningslista
  → beslutsrunda (skills/video-regler) → klipp i molnet → granskning → Discord → Postiz
```

Kod: `engine/references/` (`fetch`, `measure`, `breakdown`, `adapt`, `service`, `mcp`), modell `ReferenceVideo`
(migration 0038). Referensens fil är aldrig en `MediaAsset` – den kan inte hamna i ett klipp av misstag.

## Verktyg

| MCP-verktyg | Vad |
|---|---|
| `analyze_reference_video(url)` | Hämta, mät och bryt ner. Samma fil två gånger återanvänds. |
| `list_reference_candidates` | Bevakade annonser: längst körda (aktiva väger dubbelt), sedan EU-räckvidd; varje annonsörs bästa först. |
| `get_reference`, `list_references`, `view_reference_sheet` | Läs nedbrytning, mätningar och kontaktkarta. |
| `reanalyze_reference(model)` | Bryt ner igen med en annan modell; alla körningar sparas. |
| `plan_our_version(angle, notes)` | Vår version för bolaget. Påhittade asset-id och overifierade fakta tas bort med varning. |

Lokalt utan databasskrivningar: `python manage.py reference_lab --company Faiv --top 3 --models a,b --adapt` eller
`--url <länk>`; resultat i `work/references/`.

Dagligen (`run_daily`, steget `reference_breakdown`): högst `REFERENCE_DAILY_LIMIT` (2) nya bevakade annonser per bolag
som gått minst `REFERENCE_MIN_DAYS` (14) dagar bryts ner automatiskt. En annons utan video provas en gång.

## Modellval och kostnad (uppmätt 2026-10-13, 3 FAIV-konkurrentannonser à 9–11 s)

| Modell | Kostnad/annons | Tid | Bedömning |
|---|---|---|---|
| `google/gemini-3.1-flash-lite` | ≈ 0,003 USD | 6 s | För svag: missade övergångar och musik ("ingen musik" när det fanns), blandade ihop skärmtext och tal. |
| **`google/gemini-3.8-flash`** (standard) | ≈ 0,012–0,020 USD | 30–45 s | Mest detaljerad: övergångar, musik och BPM, hela voiceovern, återanvändbara grepp. |
| `google/gemini-3.1-pro-preview` | ≈ 0,040–0,058 USD | 29–41 s | Lika bra som Flash, ibland ett ljud mer; 3× dyrare. Använd vid behov via `reanalyze_reference`. |

Video kostar ≈ 90 tokens/s i inmatning; det mesta av kostnaden är modellens svar (inklusive tänkande). Vår version
kostar ≈ 0,017–0,024 USD med Flash. Hela jämförelsen inklusive tre "vår version": ≈ 0,26 USD.

## Kända begränsningar

- **Facebook begränsar Ad Library** (HTTP 429 efter ~8 hämtningar i följd). Hämta en i taget; dagliga steget gör högst 2.
  Från GitHub Actions/Render-IP är gränsen inte testad än.
- **Apify-aktören `eiv/meta-ads-library-scraper` ger ingen bild- eller videolänk** (fälten `videoUrl`/`imageUrl` finns inte i
  svaret). Videon hämtas därför från annonsens Ad Library-sida. Aktören ger däremot `euTotalReach`, som nu sparas per
  observation (`metrics`) och används i rankingen.
- Instagram kräver ibland inloggning för att visa en video; då säger verktyget det och användaren kan ladda upp filen.
- Klippmätningen hittar hårda klipp bildruteexakt och de flesta blixtar/övertoningar; layoutbyten mitt i en övergång kan
  missas – nedbrytningsmodellen får då dela scenen och säger det i `observations`.
- Apifys gratisplan tillåter 5 samtidiga körningar och bolagets dagliga skraptak (1 USD) nåddes vid första hämtningen
  2026-10-13; resterande FAIV-annonssidor (Strands, Vparts, Nordic Lights, egen sida) hämtas av nästa dagliga körning.

## Bevakning aktiverad 2026-10-13

Startlistorna i `library/follow-lists/` hade aldrig aktiverats i produktion (FAIV hade 0 konton och 0 annonser).
Aktiverat: FAIV 9 IG-konton + 10 annonssidor, Golfkuponger 4 IG-konton + 2 annonssidor. Första annonshämtning FAIV:
132 annonser från 6 sidor (≈ 0,56 USD).
