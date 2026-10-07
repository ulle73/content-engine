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
| `type` | `template` (hel video/karusell) · `scene` · `effect` · `transition` · `text` (textanimation/typografi) · `caption` · `grade` (färgsättning) · `background` · `carousel` · `skill` · `prompt` · `sound` · `tool` |
| `medium` | `video` · `carousel` · `image` · `audio` · `text` |
| `formats` | `9:16` · `1:1` · `4:5` · `16:9` · `any` |
| `engine` | `hyperframes` · `remotion` · `html-playwright` · `python` · `canvas` · `none` |
| `cost` | `free` · `paid` (ange tjänst i `requires`, t.ex. `api:kie.ai`) |
| `status` | `verified` (renderad och granskad) · `unverified` · `broken` (beskriv i `notes`) |
| `preview` | `null` eller `{ "video": "library/previews/<id>.mp4", "still": "library/previews/<id>.jpg" }` |

`id` är unikt i hela biblioteket: `<kit>.<del>.<namn>`, gemener och bindestreck.
