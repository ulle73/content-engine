# Golfkuponger – 3D-element i Blender

Riktig 3D (ljus, metall, djup) som **genomskinliga klipp** att lägga ovanpå våra filmer i Remotion, HyperFrames,
FilmCraft eller Resolve. Blender körs headless (`tool-blender`), inget GUI behövs. Katalog-id:n:
`golfkuponger.blender3d.mall`, `.titel`, `.golfboll` (`python library/tools/find.py 3d`).

| Effekt | Vad händer | Standard |
|---|---|---|
| `titel` | 3D-rubrik i guld `#D6A536` snurrar 270° in ur djupet, landar mjukt, ljussvep över guldet, lätt gungning | "MER GOLF", 800 px bred, mitt x 497 / y 620, 0,9 s in + läsregel |
| `golfboll` | Golfboll (336 dimplar i geometrin) faller in från höger, studsar tre gånger och rullar till vila, med kontaktskugga | 420 px, vila x 497 / y 960, 1,8 s in + 1,2 s vila |

## Kör

```bash
python library/templates/golfkuponger-blender-3d/render.py titel --out work/<projekt>/3d/titel --test --set text="MER GOLF"
python library/templates/golfkuponger-blender-3d/render.py titel --out work/<projekt>/3d/titel --set text="MER GOLF"
python library/templates/golfkuponger-blender-3d/render.py golfboll --out work/<projekt>/3d/boll --set y=1090 --set diameter_px=300
```

1. **`--test` först** (50 %, 16 samples, ~0,3 s/bildruta). Titta på `kontroll-magenta.png` och `<namn>-forhand.mp4`.
2. Full rendering (100 %, 64 samples): titel ~1,5 min, golfboll ~2 min på Radeon 860M.
3. `--bara-bilder 10,27,60` renderar bara de bildrutorna (stillbildskontroll på några sekunder).
4. `--set blend=work/<projekt>/3d/titel.blend` sparar scenen så att den kan öppnas och finputsas i Blender-GUI:t.

Alla nycklar står överst i `blender3d.py`. Vanligast: `text` (`\n` = ny rad), `color`, `font`, `x`/`y` (motivets mitt i
px i 1080×1920), `bredd_px`, `diameter_px`, `studs_px`, `intro`/`frames` (bildrutor), `exit=spin`, `engine=CYCLES`.

## Utdata (i `--out`)

| Fil | Till |
|---|---|
| `<namn>.webm` | VP9 med alfa (`yuva420p`) – Remotion `<OffthreadVideo transparent>`, HyperFrames, webben |
| `<namn>.mov` | ProRes 4444 med alfa (`yuva444p10le`) – FilmCraft, DaVinci Resolve, Premiere |
| `frames/f_0001.png …` | PNG-sekvens RGBA (källan; bäst kvalitet) |
| `<namn>-forhand.mp4` | Förhandsvisning över mörkgrönt `#082f27` (ingen alfa) |
| `kontroll-magenta.png` | 4 bildrutor på magenta med röda safe zone-linjer – halo och smutsiga kanter syns direkt |
| `qa.json` | Motivets ruta i px per bildruta, safe zones och läsregel |

`render.py` stoppar (exitkod ≠ 0) om läsregeln bryts (titel), om motivet hamnar utanför safe zones när det har landat,
om en fil inte avkodas till rätt antal bildrutor eller om WebM-alfan saknas.

## Lägga klippet i en film

**Remotion** (exempel i `remotion-exempel/`, Remotion 4.0.530 från `motion-renderer/node_modules`):

```jsx
<Sequence from={39}><OffthreadVideo src={staticFile('golfboll.webm')} transparent muted /></Sequence>
```

`transparent` gör att Remotion extraherar PNG i stället för BMP, så alfan följer med (Remotion ≥ 4.0.0,
https://www.remotion.dev/docs/offthreadvideo#transparent). Nya `<Video>` från `@remotion/media` rekommenderas för
vanlig video, men dess dokumentation lovar inte alfa – använd `OffthreadVideo` för de här klippen.

```bash
node library/templates/golfkuponger-blender-3d/remotion-exempel/render.mjs work/<projekt>/exempel-public work/<projekt>/exempel.mp4 props.json
```

`publicDir` innehåller `film.mp4` och klippen; `props.json` t.ex.
`{"film":"film.mp4","filmFran":13.0,"langd":4,"lager":[{"src":"golfboll.webm","start":0.1}]}`.

**HyperFrames:** `<video src="golfboll.webm" muted playsinline>` i en klippdel – Chrome spelar VP9-alfa.
**FilmCraft/Resolve:** lägg `.mov` på ett spår ovanför filmen.

## Regler som gäller (skills/video-regler, skills/ljud)

- **Safe zones** x 65–929, y 270–1250 för motivet när det står still (kontrolleras). Inrörelsen får passera kanten.
- **Text mot mitten:** rubriken ligger på y ≈ 620 som standard; står bollen eller ett annat motiv mitt i bild, lägg
  rubriken ovanför (`--set y=420`).
- **Läsregeln:** rubriken står still minst max(5/6, tecken/12) + 0,9 s – annars stoppar skriptet.
- **Färger:** `view_transform = 'Standard'` (AgX bleker guldet). Guldet är `#D6A536` (experiment-site-temat).
- **Ljud ingår inte.** Välj ljud i filmen enligt `skills/ljud`: riktiga ljud ur ljudbanken (t.ex. en bollstuds per
  nedslag – tiderna står i `qa.json` som bildrutor), ljudprovning, aldrig syntade effekter.
- **Inget laddas ner.** Studioljuset är procedurellt (gradient + area lights). En HDRI från Poly Haven kan ge rikare
  reflexer i guldet – fråga användaren först (`tool-blender`).

## Vidare

- Golfkupongers logga som tryck på bollen (bildtextur) och SVG-loggan extruderad i guld (`bpy.ops.wm.svg_import`).
- Fler effekter i samma skript: kupong/kort som vänds i 3D, guldkonfetti, boll i hål.
