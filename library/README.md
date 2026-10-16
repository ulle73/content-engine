# Content Library

Allt som behövs för att skapa innehåll snabbt och snyggt: färdiga mallar, effekter, övergångar,
karuseller, skills och prompts. **Börja alltid härifrån** — välj en färdig mall, justera sedan.
Ingången är skillen `studio` (`skills/studio/SKILL.md`, i Claude Code: `/studio`).

> Repot ska vara **privat**: `kits/` innehåller köpt/nedladdat tredjepartsmaterial utan
> licens för vidarespridning. Använd det för egna produktioner, publicera det inte vidare.

## Struktur

```
library/
  catalog.json        genererad: alla poster från alla LIBRARY.json (sök här)
  gallery.html        genererad: bläddra visuellt, filtrera på typ/format/taggar
  kits/<kit>/         importerade kit (rensade, Windows-anpassade) + LIBRARY.json
  effects/<id>/       egna effekter/övergångar (HyperFrames) + LIBRARY.json
  templates/<id>/     egna kompletta mallar (t.ex. golfkuponger-friskvard-promo)
  prompts/            promptmallar (regissörsbrief, kritikloop, varumärkesprompt …) + LIBRARY.json
  recipes/<id>/       produktionsrecept: RECIPE.md + recipe.json (schema recipe/v1) + LIBRARY.json
  models/<modell>/    model playbooks: PLAYBOOK.md per AI-modell; models/README.md = routning scentyp → modell
  external/           index över externa bibliotek (HyperFrames-registret, Remotion-katalogen,
                      öppna repon) — pekar ut, kopierar inte
  previews/<id>.*     förhandsvisningar (liten mp4/webm + jpg)
  tools/              build_catalog.py, render_previews.py
```

Kitens skills ligger dessutom som Claude Code-skills i `.claude/skills/<namn>/` så att de laddas
automatiskt när Claude Code körs i repot.

## Lägg till något

1. Lägg filerna i rätt mapp.
2. Lägg till en post i mappens `LIBRARY.json` (format nedan).
3. Kör `python library/tools/build_catalog.py` — bygger om `catalog.json` och `gallery.html`.
4. Verifiera: rendera en förhandsvisning, titta på den, sätt `status: "verified"`.

## Postformat (`LIBRARY.json`)

```json
{
  "kit": "nextphase",
  "title": "NextPhase Skill Pack",
  "source": { "name": "NextPhase (Jad)", "url": "", "license": "Ingen licens angiven – endast egen användning" },
  "items": [
    {
      "id": "nextphase.motiongraphics.light-leak",
      "name": "Ljusläcka flash-through",
      "type": "transition",
      "medium": "video",
      "formats": ["16:9", "9:16", "1:1"],
      "engine": "hyperframes",
      "description": "Violettvit strimma blommar, vitnar ut och avslöjar nästa scen (12 frames).",
      "tags": ["light-leak", "flash", "premium", "glow"],
      "path": "library/kits/nextphase/skills/motiongraphics/components/mg-motion-library.html",
      "use": "Skill /motiongraphics, eller kopiera .mg-leak-blocket in i en komposition",
      "requires": ["hyperframes", "chrome"],
      "cost": "free",
      "status": "unverified",
      "verified_at": null,
      "preview": null,
      "notes": ""
    }
  ]
}
```

| Fält | Värden |
|---|---|
| `type` | `template` (hel video/karusell) · `scene` · `effect` · `transition` · `text` (textanimation/typografi) · `caption` · `grade` (färgsättning) · `background` · `carousel` · `skill` · `prompt` · `sound` · `tool` · `recipe` (produktionsrecept) · `model` (model playbook) |
| `medium` | `video` · `carousel` · `image` · `audio` · `text` |
| `formats` | `9:16` · `1:1` · `4:5` · `16:9` · `any` |
| `engine` | `hyperframes` · `remotion` · `html-playwright` · `python` · `canvas` · `blender` (3D, headless bpy) · `none` |
| `cost` | `free` · `paid` (ange tjänst i `requires`, t.ex. `api:kie.ai`) |
| `status` | `verified` (renderad och granskad) · `unverified` · `broken` (beskriv i `notes`) |
| `preview` | `null` eller `{ "video": "library/previews/<id>.mp4", "still": "library/previews/<id>.jpg" }` |

`id` är unikt i hela biblioteket: `<kit>.<del>.<namn>`, gemener och bindestreck.

## Recept och modell-playbooks (produktionsmotorn, MASTERPLAN §4b)

**Recept** (`library/recipes/<id>/`) är den återanvändbara enheten för film (D11): `RECIPE.md` (idé, regi per scen,
klipprytm, text, ljud, varianter, AI-uppgraderingar) + `recipe.json` som maskiner läser. Catalog-id: `recipe.<id>`
(post i `library/recipes/LIBRARY.json`, med fältet `company`). `get_content_library_item` returnerar hela `recipe.json`.

`recipe.json` följer **exakt** schemat `recipe/v1` (andra agenter och kod beror på det):

| Fält | Innehåll |
|---|---|
| `schema` | `"recipe/v1"` |
| `id`, `title` | mappnamn (gemener-bindestreck), svensk titel |
| `company` | `faiv` · `golfkuponger` · `any` |
| `type` | `before-after` · `sketch` · `pov` · `product-in-context` · `tips` · `seasonal` · `testimonial` · `mood` · `match-cut` |
| `formats`, `duration_s` | t.ex. `["9:16","4:5","1:1"]`, `15`; scenernas längder summerar till `duration_s` (±0,5 s) |
| `hook`, `why_it_works` | kroken (första 1–2 s, svenska) och varför formatet fungerar |
| `references` | `[{label, url}]`, minst en |
| `music` | `{mood, bpm (heltal/null), library_id (sound-post i katalogen eller null)}` |
| `scenes[]` | `{id, purpose, duration_s, source, footage_ids, catalog_query, ai_upgrade, text, effects, transition_in, camera, notes}` |
| `cta` | `{text, landing}` (`brand` · `product` …) |
| `qa` | checklista |
| `status` | `draft` · `verified` |

Scenregler (kontrolleras av `build_catalog.py`): `source` är `footage` · `product_image` · `graphic` · `ai_video` · `ai_image`.
AI som huvudkälla kräver `ai_upgrade: {model, prompt_template}` som beskriver genereringen; för andra källor är
`ai_upgrade` ett valfritt AI-alternativ för scenen (`model` är en mapp i `library/models/`). De 12 första recepten
fungerar med enbart eget material, men det är ett val, inte en regel. `footage_ids` måste finnas i `docs/FILMLISTA.md`; `product_image` kräver
`catalog_query` (produktkatalogen). `effects` är katalog-id:n (effekt, caption, text, grade, sound …) och `transition_in`
en `transition`-post. Påståenden skrivs som `{fact:F4}` och måste finnas i bolagets faktaskill (`faiv-fakta` /
`golfkuponger-friskvard`) – de visas bara när faktat är verifierat i appens faktabank. Övriga `{platshållare}` är fria.

**Från recept till färdig video:** `engine/edit/planner.py` (MCP `plan_cut_from_recipe` → `render_recipe`) bygger en
klippspec `cut/v1` ur receptet och mediabanken: klipp vars taggar innehåller scenens filmlista-id (sätts med MCP
`tag_media`, i mediabibliotekets fildialog, eller automatiskt när filnamnet innehåller id:t, t.ex. `fa-m1_volvo.mp4`),
produktbilder via `catalog_query`, CTA-grafik som slutkort/slutbild. Det som saknas listas som `missing` (vad som ska
filmas). Ofullständiga recept går att klippa med `allow_missing`. Ett säkert alternativ i en scens `notes` skrivs som
`Annars: '…'` – det används när faktat inte är verifierat. Färdiga klipp får en billig AI-granskning (1–10 + tre
rättningar per scen) på Discord-kortet.

**Model playbooks** (`library/models/<modell>/PLAYBOOK.md`, catalog-id `model.<modell>`): styrkor/svagheter, promptformat,
parametrar, kameraord, fallgropar och exempel för våra recept, med källor. `library/models/README.md` är routningen
scentyp → modell (D10). Modellregistret i `engine/creative_registry.py` är sanningen om vad som är tillgängligt.
