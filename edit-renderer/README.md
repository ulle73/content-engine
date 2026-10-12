# edit-renderer – klippning i molnet

Klipper en färdig video från en **cut spec** (`cut/v1`) med HyperFrames på GitHub Actions, utan ägarens dator.

```
Claude/ChatGPT ─ MCP render_cut ─► content-engine (Render)          GitHub Actions (gratisminuter)
                                    EditJob: queued ── dispatch ──►  .github/workflows/edit-render.yml
                                                                      node src/worker.js
                                    /internal/edit/claim/   ◄──────── claim (väntar ut Render-kallstart ~2 min)
                                    /internal/edit/assets/… ◄──────── hämtar media (direkt från R2 när det går)
                                    /internal/edit/heartbeat/ ◄────── var 30:e s
                                                                      beats + bildanalys → compose → hyperframes check
                                                                      → render → musik + SFX + ducking → loudnorm −14 LUFS
                                                                      → H.264/yuv420p/faststart (+ preview) → teknisk QA
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

## Kvalitetsgrind

Efter AI-granskningen (`engine/edit/critic.py`) avgör `engine/edit/gate.py` om klippet går till Discord som klart.
Det hålls tillbaka som **behöver omtag** när AI-betyget är under `EDIT_GATE_MIN_SCORE` (7) eller när mer än
`EDIT_GATE_MAX_STILL_SHARE` (0,5) av scentiden är stillbilder. Skälen och kritikens första rättning syns i
`get_cut_job` (`quality_gate`, `next_step`). En granskning som inte kunde köras stoppar inget. Ägaren kan ändå skicka
klippet med MCP-verktyget `send_cut_for_review`. `EDIT_QUALITY_GATE=0` stänger av grinden. Renderarens mätdata
(`beats`, `sfx`, `typography`, `qa`) sparas i `cut_spec.render`, och granskningsmanifestet använder de beat-synkade
scentiderna.

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
| Övergångar | cut, fade, blur, flash (genom vitt), whip och push (med riktad rörelseoskärpa), speed-ramp (cut-the-curve), zoom, wipe (med accentkant, även före/efter-wipe), iris, light-leak, glitch |
| Effekter | ken-burns, push-in, pull-back, punch-in, beat-punch (puls på ettorna), drift (handhållen), shake, dark-to-light, focus-rack, grain, vignette, light-sweep, leak-overlay, glow, logo-sting, logo-reveal |
| Gradering | grade-warm, grade-noir, grade-duotone (varumärkesfärg), grade-cool, grade-forest, grade-tomato |
| Textstilar | rise, line-reveal, slam, blur-in, typewriter, tracking-in, cascade, highlight (markeringspenna), shimmer, extrusion (3D), lower-third, scramble, caption (ord för ord), chunk (2–4 ord, hårdklipp) |
| Captions som effekt | caption-chunk (`nextphase.zak.caption`), caption-words, caption-marker – sätter textstilen när `text_style` saknas |
| Ljud (effekter) | sfx-whoosh, swish, impact, boom, riser, swell, pop, tick, click, snap, chime, shimmer, tapestop, room-tone (`motion-studio.sound.*`, `ext.content-engine-motion.audio.*`) |

## Finish (det som gör klippet proffsigt)

- **Beat-synk** (`src/beats.js`): med musik körs `hyperframes beats` (annars ffmpeg + spektralflux i JS) → stadigt
  taktgaller (tempo, fas, ettor). Scengränser flyttas till närmaste taktslag inom ±0,3 s (högst 0,6 slag), aldrig
  under 0,8 s per scen och aldrig förbi videons slut; totallängden ändras högst 0,3 s. Övergångar hamnar därmed på
  takten, texter landar på nästa slag, slam-ord och captions byts i takt. Galler och flyttar sparas i `meta.beats`
  och sammanfattas i en varning. Stäng av med `EDIT_BEAT_SYNC=0`.
- **Typografi** (`src/typeset.js`): typskala (1,25) per format, balanserade radbrytningar med svenska regler (aldrig
  ett ensamt ord på sista raden, aldrig radslut efter småord som "på/i/och", siffra + enhet hålls ihop, ≤ 22 tecken
  per rad för 9:16-krokar), kerning/ligaturer, tätare spärrning i stora grader. Radbrytningen räknas i webbläsaren
  med uppmätta ordbredder (samma funktion som testas i Node).
- **Typsnitt**: Inter, Anton, Caveat Brush och Playfair Display ligger i `fonts/` (OFL, se `fonts/OFL.txt`).
  Varumärkets `font_family` mappas dit (serif → Playfair med kursiva betoningsord); okända typsnitt ger en varning.
- **Läsbarhet** (`src/legibility.js`): bilden under texten samplas (ffmpeg) och texten får skugga, en scrim med
  uträknad styrka eller en platta så att vit text når WCAG-kontrast; `hyperframes check` verifierar kontrasten.
- **Säkra ytor** (`src/safezones.js`): Reels/TikTok (topp 12 %, botten 22 %, höger 14 %), 4:5, 1:1 och 16:9 har
  egna zoner. Runtime rapporterar uppmätta textboxar (`[cut-layout]`) som jämförs mot zonerna före rendering.
- **Look**: varumärkets färgmatris (svärta mot bakgrundsfärgen, högdagrar mot accenten), lätt korn och vinjett i
  alla scener (`brand.look = "none"` stänger av), alltid kamerarörelse, tre easing-kurvor.
- **Ljud** (`src/sfx.js`): syntetiserade whoosh/impact/shimmer på övergångar, impact på krokens slam och en riser in
  i slutbilden; ca 15 dB under musiken, duckas under klippljud. Bara när det finns musik eller klippljud att ligga
  under (`EDIT_AUTO_SFX=0` stänger av). Slutbilden behåller sitt originalljud.
- **Teknisk QA** (`src/qa.js`) efter rendering: svarta och frysta bilder, blixtar (> 3/s), klippt ljud, tysta
  glapp och ljudnivå vs −14 LUFS → varningar i jobbet och `meta.qa`.

## Köra lokalt

```bash
cd edit-renderer
node src/cli.js smoke-media     # skapar två testklipp i ../work/edit-smoke/media (ffmpeg)
npm run smoke:dry               # bygger kompositionen + hyperframes check (lint, kontrast, säkra ytor)
npm run smoke                   # full rendering → ../work/edit-smoke/master.mp4 (+ preview.mp4)
HF_LINT=1 npm test              # alla behandlingar i alla format, med lint
node src/cli.js contact-sheet ../work/edit-smoke/master.mp4 ../work/edit-smoke/sheet.png   # bildark för granskning
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
