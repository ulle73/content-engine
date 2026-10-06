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
| MCP | `engine/ad_studio/mcp.py` | 13 verktyg, registrerade i `engine/mcp_server.py` |

## Flödet i MCP

1. `read_ad_skill` för `golfkuponger-brand` och `golfkuponger-friskvard`.
2. `start_ad_brief(message)`. Svaret innehåller `missing` och `next_question`.
3. Frågor och förslag. Varje beslut sparas med `update_ad_brief(changes, expected_revision)`.
4. Bilder: `search_ad_assets(query, role)`, visa med `view_media`, och låt användaren välja. Nya uppladdningar går via befintliga ingest-verktyg.
5. Remotion: `get_ad_template_blueprint(template_id)` ger exakta scener, tider och text- och bildplatser.
6. `lock_ad_brief` när användaren säger kör. Den misslyckas med exakta skäl om något saknas.
7. `produce_ad` skapar ett Motion-projekt av exakt den låsta briefen. Sedan körs befintliga `render_motion_project` (preview), `approve_motion_preview` och final.

## Garantier

- Produktionen läser bara en låst brief vars hash stämmer.
- Mallarnas standardtexter (som innehåller overifierade påståenden som "300+ klubbar" och "31/12") används aldrig. Varje textplats måste fyllas i briefen.
- Påståenden ligger i `facts` och blockerar låsning tills de är verifierade.
- Higgsfield kräver godkänd kostnad i briefen. Generering sker via befintliga granskade mediaverktyg.
- Optimistisk låsning via `expected_revision`, och allt är scopat till företaget.

## Bildbanken

`list_untagged_media`, sedan `view_media`, sedan `tag_media_asset`: AI:n tittar på bilden och sparar vad den visar. Det kostar inga extra API-anrop, eftersom assistenten själv ser bilden. Sätt `verified` när en människa bekräftat. `search_ad_assets` rankar på betydelse och föredrar verifierade taggar.

## Inte byggt än

- Bildväljar-widget (rutnät med kryssrutor och uppladdning) i MCP-appen. Idag sker valet i chatten.
- Automatisk QA av renderade frames mot brand-checklistan.
- Fler Remotion-mallar utöver friskvårdsmallarna.
