# edit-renderer – klippning i molnet

Klipper en färdig video från en **cut spec** (`cut/v1`) med HyperFrames på GitHub Actions, utan ägarens dator.

```
Claude/ChatGPT ─ MCP render_cut ─► content-engine (Render)          GitHub Actions (gratisminuter)
                                    EditJob: queued ── dispatch ──►  .github/workflows/edit-render.yml
                                                                      node src/worker.js
                                    /internal/edit/claim/   ◄──────── claim (väntar ut Render-kallstart ~2 min)
                                    /internal/edit/assets/… ◄──────── hämtar media (direkt från R2 när det går)
                                    /internal/edit/heartbeat/ ◄────── var 30:e s
                                                                      compose → hyperframes lint → render
                                                                      → musik + ducking → loudnorm −14 LUFS
                                                                      → H.264/yuv420p/faststart (+ preview)
                                    /internal/edit/output/… ◄──────── multipart upload
                                    store_asset → Review → Discord
```

- **Server**: `engine/edit/` (modell `EditJob`, `spec.py` validering, `service.py` kö/dispatch/återhämtning,
  `worker_api.py`, `mcp.py` med `render_cut` och `get_cut_job`).
- **Utlösning**: `render_cut` skickar `workflow_dispatch` (env `GITHUB_DISPATCH_TOKEN`). Saknas token ligger jobbet
  kvar i kön; det dagliga workflowet kör `python manage.py edit_jobs --no-discord` som startar Edit Render med
  `github.token`. En körning tar upp till 3 köade jobb.
- **Återhämtning**: jobb vars lease gått ut köas om (max 3 försök). Misslyckad Discord-post fäller aldrig jobbet;
  den görs om vid nästa claim (på Render, där `APP_URL` stämmer).

## Master och förhandsvisning (valt)

Mastern (≤ 80 MB, x264 CRF 18 `slow`, bitratetak efter längd, AAC 192k, `+faststart`) sparas alltid som
`EditJob.output_asset` – det är den som ska publiceras. Blir mastern större än 9,5 MB kodas även en
förhandsvisning (två pass, 720p under ~2 Mbit/s) som laddas upp separat; **granskningen i Discord använder då
förhandsvisningen** så att den bifogas och spelas direkt i mobilen. Mastern nås från granskningen via
`review.edit_jobs` och `get_cut_job` (`output_asset_id`).

## Cut spec v1

Se docstring i `engine/edit/spec.py` (validering med svenska felmeddelanden). Kort:
scener med `asset_id` (video/bild från bolagets mediabank), `duration_s`, `trim_start_s`, `fit` (`cover`/`contain`),
`text` (ord inom `*stjärnor*` får accentfärgen), `text_style`, `text_position`, `audio` (`mute`/`keep`),
`effects`, `transition_in`; plus `music_asset_id`, `music_volume` och `cta` (slutkort med logga, text och url-pill).
Max 90 s inklusive slutkort. Okända eller ej stödda biblioteks-id hoppas över med en varning i jobbet.

## Vad mallen stöder (support.json)

Katalog-id mappas till inbyggda behandlingar i `support.json` (samma fil läses av Python). Varje behandling kan
också anges direkt som `cut.<typ>.<namn>`, t.ex. `cut.effect.dark-to-light`.

| Typ | Inbyggda behandlingar |
|---|---|
| Övergångar | cut, fade, blur, flash (genom vitt), whip, zoom, push, wipe (med accentkant), iris, light-leak, glitch |
| Effekter | ken-burns, push-in, pull-back, punch-in, drift (handhållen), shake, dark-to-light, focus-rack, grain, vignette, light-sweep, leak-overlay, glow |
| Gradering | grade-warm, grade-noir, grade-duotone (varumärkesfärg), grade-cool, grade-forest, grade-tomato |
| Textstilar | rise, line-reveal, slam, blur-in, typewriter, tracking-in, cascade, highlight (markeringspenna), shimmer, extrusion (3D), lower-third, scramble, caption (ord för ord) |

Stillbilder får Ken Burns och video en lätt push om ingen kamerarörelse anges. Text hamnar inom plattformarnas
säkra yta för 9:16, 4:5, 1:1 och 16:9 och krymps tills den får plats. Typsnitt: Inter och Anton (OFL, i
`template/fonts/`); varumärkets färger kommer från `engine/motion/brand.py`.

## Köra lokalt

```bash
cd edit-renderer
node src/cli.js smoke-media     # skapar två testklipp i ../work/edit-smoke/media (ffmpeg)
npm run smoke:dry               # bygger kompositionen + hyperframes lint
npm run smoke                   # full rendering → ../work/edit-smoke/master.mp4 (+ preview.mp4)
HF_LINT=1 npm test              # alla behandlingar i alla format, med lint
```

Mot en server: `CONTENT_APP_URL=… CONTENT_EDIT_WORKER_TOKEN=… node src/worker.js`.

## Konfiguration

| Var | Namn | Värde |
|---|---|---|
| Render (content-engine-mcp) | `EDIT_WORKER_TOKEN` | slumpad sträng ≥ 32 tecken |
| Render | `GITHUB_DISPATCH_TOKEN` | fine-grained token, repo `ulle73/content-engine`, *Actions: Read and write* |
| Render | `GITHUB_REPOSITORY` | `ulle73/content-engine` (standard) |
| GitHub Secrets | `CONTENT_EDIT_WORKER_TOKEN` | samma värde som `EDIT_WORKER_TOKEN` |
| GitHub Secrets (valfri) | `CONTENT_APP_URL` | standard `https://content-engine-mcp.onrender.com` |
