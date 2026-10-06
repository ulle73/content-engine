# Ad Studio

Chatten som idémotor: "jag vill göra en ad med budskapet att använda friskvårdsbidraget innan det brinner inne" → smarta frågor → vinklar → bildförslag → Remotion eller Higgsfield → storyboard → lås → produktion.

## Delar

| Del | Fil | Ansvar |
|---|---|---|
| Kontrakt | `engine/ad_studio/brief.py` | `AdBrief`: vad som är bestämt, vad som saknas (`missing`), regelbrott (`problems`), `lock()` med hash |
| Lagring | `engine/ad_studio/models.py` | `AdDraft` (brief + revision + status), `AssetTags` (sökbar bildbank) |
| Logik | `engine/ad_studio/service.py` | Företagsscopat: starta, uppdatera, låsa, öppna igen, producera, tagga, söka |
| Mallbrygga | `engine/ad_studio/blueprints.py` | Remotion-mall → scenskelett; låst brief → mallfält |
| Kunskap | `skills/*/SKILL.md` | Brand och friskvård. Läses av AI:n via `read_ad_skill` |
| Bilder i chatten | `engine/ad_studio/sheets.py` | Numrerat bildark, storyboard-skiss och granskningsark (Pillow, ingen kostnad) |
| MCP | `engine/ad_studio/mcp.py` | 18 verktyg, registrerade i `engine/mcp_server.py` |

## Studion i appen (verkstaden)

Menyn **Annonser** (`/company/<id>/annonser/`) visar samma utkast som MCP skapar. Där kan man:

- starta en annons med ett budskap,
- välja mall och få scenerna upplagda,
- skriva text per scen,
- välja bild per scen i ett rutnät med förslag överst, eller ladda upp en ny bild som taggas direkt,
- bocka i verifierade påståenden,
- se storyboarden stort,
- låsa, producera och öppna Motion-projektet för preview och rendering.

Varje MCP-svar har `studio_url`, så chatten kan länka hit med *Öppna i studion*. Chatten och studion är samma utkast med samma revision. Den som sparar på en gammal revision får ett tydligt meddelande om att utkastet har ändrats.

## Flödet i MCP

Detaljerna står i `skills/ad-studio/SKILL.md`. I korthet:

1. `read_ad_skill` för `ad-studio`, `golfkuponger-brand` och domänskillen.
2. `start_ad_brief(message)`. Svaret innehåller `missing` och `next_question`.
3. Första svaret är en komplett rekommendation: tre vinklar, motor och mall, och max tre frågor med färdiga svar.
4. Bilder: `suggest_scene_assets`, sedan `show_ad_images` (numrerat ark, användaren svarar "ta 2 och 5"). Bilder som klistras in i chatten sparas, taggas och kopplas med `add_ad_image`.
5. Remotion: `get_ad_template_blueprint(template_id)` ger exakta scener, tider och text- och bildplatser.
6. `update_ad_brief` och sedan `preview_ad_storyboard` (hela annonsen som en bild, med safe zones och regelbrott). Iterera.
7. `lock_ad_brief`, `produce_ad`, `render_motion_project` (preview).
8. `review_ad_render`: nyckelbilder med safe zones, poängsatta mot checklistan, innan `approve_motion_preview` och final.

## Garantier

- Produktionen läser bara en låst brief vars hash stämmer.
- Mallarnas standardtexter (som innehåller overifierade påståenden som "300+ klubbar" och "31/12") används aldrig. Varje textplats måste fyllas i briefen.
- Påståenden ligger i `facts` och blockerar låsning tills de är verifierade.
- Higgsfield kräver godkänd kostnad i briefen. Generering sker via befintliga granskade mediaverktyg.
- Optimistisk låsning via `expected_revision`, och allt är scopat till företaget.

## Bildbanken

`list_untagged_media`, sedan `view_media`, sedan `tag_media_asset`: AI:n tittar på bilden och sparar vad den visar. Det kostar inga extra API-anrop, eftersom assistenten själv ser bilden. Sätt `verified` när en människa bekräftat. `search_ad_assets` rankar på betydelse och föredrar verifierade taggar.

## Faktabank

**Annonser → Faktabank** (`/annonser/fakta/`, MCP: `list_ad_facts` och `propose_ad_fact`) samlar de påståenden Golfkuponger får använda. Varje påstående har status *verifierad*, *ej verifierad* eller *får inte användas*.

- Första gången banken används kopieras startvärdena från skillen `golfkuponger-friskvard` in. Skattepåståenden börjar som spärrade.
- Briefens `facts` kopplas till banken via `fact_id`, eller via exakt samma formulering, och får sin status därifrån.
- AI:n kan föreslå påståenden men aldrig verifiera dem: MCP-uppdateringar nollställer `verified`.
- Den som ändrar formuleringen nollställer verifieringen.
- Ett spärrat påstående stoppar låsningen.

## Mallar

Mallarna är definierade i `engine/motion/ad_templates.py`, och katalogen genereras med `scripts/generate_motion_catalog.py`. Tre mallar har ton och tempo: `golf-fracka` (fräck, 12 s), `golf-sista-chansen` (brådskande, 10 s, nedräkning) och `golf-premium` (lugn, 15 s). De har ingen standardtext, så varje ord kommer från briefen. Renderarens `spec.schema.json` måste exporteras om (`PYTHONPATH=. python scripts/export-motion-schema.py` och sedan prettier) när mallar läggs till. Ett test fångar avvikelser.

## Inte byggt än

- Klickbar widget direkt i ChatGPT och Claude. Klickandet sker i studion via länken.
- Visuell variation per ton (färg och typografi). Idag skiljer sig tonerna i tempo, övergångar, musik och komponenter, men alla använder samma gröna brand-preset.
- Fler format (4:5, 1:1) för skärm-annonsmallarna.
