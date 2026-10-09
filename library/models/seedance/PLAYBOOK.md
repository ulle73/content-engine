# Seedance – playbook (2.0 · 2.5)

> Fakta kontrollerade 2026-10-09. "Officiellt" = Higgsfields API-referens/hjälpcenter eller ByteDance Seed.
> Higgsfields promptguide bygger på deras egna tester, inte på ByteDance. BytePlus ModelArk-dokumentationen
> (inkl. ByteDances egen Seedance 2.0-promptguide) laddas med JavaScript och kunde inte läsas – därav luckor.
> Inga betalda körningar har gjorts för den här playbooken.

## När Seedance

- **Människor och karaktärer** – reaktioner, en person vid bilen, återkommande sketchkaraktär. Referensbilder håller
  identiteten över klipp bättre än text (Higgsfield-guiden).
- **Övergångar och kedjor mellan riktiga bilder** – `image_url` + `end_image_url` (första/sista bild).
- **Längre sekvenser i en generering** – 2.5: 4–30 s med shots och hårda klipp i samma prompt.
- **Högst upplösning** – 2.0 går till 4K (≤ 15 s).
- Inte förstaval för: läsbar text/logga i bild, extrema närbilder på händer, flera personer som pratar samtidigt.

## Styrkor / svagheter

| | |
|---|---|
| + | Mänsklig rörelse och ansikten; multi-shot-berättande i en prompt (Higgsfield-guide). |
| + | Native ljud inkl. läppsynk "på flera språk" (Higgsfield hjälpcenter) – **svenska ej specifikt dokumenterat**. |
| + | Referenser: `@character`, `@style`, `@motion` (video), `@audio`. 2.0: 9 bilder/3 videor/3 ljud; 2.5: totalt 50 (Higgsfield hjälpcenter – appen; se API-förbehåll nedan). |
| − | Scener med flera karaktärer är svårast; karaktärer kan byta sida mellan shots (Higgsfield-guide). |
| − | Loggor/produkter beskrivna i text blir påhittade – bifoga den riktiga (kreatörer). |
| − | Text och loggor i bild, folkmassor, speglar, snabba komplexa lemrörelser är svaga (kreatörer). |
| − | Långa repliker → "grötig" mun; flerpersonsläppsynk och sång svagt (kreatörer). |

## Parametrar (Higgsfield REST)

| Endpoint | Längd | Upplösning | Slutbild | Ljud | Format |
|---|---|---|---|---|---|
| `bytedance/seedance-2.5/text-to-video` | 4–30 s | 480p/720p/1080p | – | `generate_audio`, **default true** | `aspect_ratio` 16:9, 4:3, 1:1, 3:4, 9:16, 21:9 |
| `bytedance/seedance-2.5/image-to-video` | 4–30 s | 480p/720p/1080p | `end_image_url` | `generate_audio`, **default true** | följer startbilden (inget `aspect_ratio`); `output_format` mp4/mov |
| `bytedance/seedance-2.0/text-to-video` | 4–15 s | 480p/720p/1080p/4k | – | `generate_audio`, default true | explicit `aspect_ratio` |
| `bytedance/seedance-2.0/image-to-video` | 4–15 s | 480p/720p/1080p/4k | `end_image_url` | `generate_audio`, default true | följer startbilden |

Källor: [2.5 i2v](https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference),
[2.0 i2v](https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference), `docs/2026-09-23-higgsfield-seedance-model-audit.md`.

- **Sätt alltid `generate_audio` explicit** (registret kräver det; default true).
- **Reference-to-video** (`bytedance/seedance-2.5/reference-to-video` med `image_urls[]`/`video_urls[]`/`audio_urls[]`)
  finns i API:t men är **inte aktiverat i Content Engine** (kräver flera persisterade referensroller, se audit-dokumentet).
  Elements/`@character` är alltså i dag en app-funktion för oss; i API-flödet bär startbilden identiteten.
- `seed` och `aspect_ratio` för i2v: inte dokumenterat hos Higgsfield.
- **Pris:** inte publicerat i API-referensen. Higgsfields blogg 2026-08-06: 8 s 2.5 = 52 krediter (720p) / 24 (480p), 2.0 720p = 36 krediter
  ([källa](https://higgsfield.ai/blog/seedance-2-5-pricing-2026)). fal.ai (återförsäljare, annan prislista) ≈ 0,47 USD/s 2.5 720p.
  Ljud på/av påverkar inte priset (Higgsfield hjälpcenter). Kontopris = `/estimate/`.

## Promptformat

**Higgsfields struktur för 2.5** – en prompt med märkta sektioner i denna ordning
([guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide)); matchar registrets `prompt_sections`:

```
GLOBAL STYLE: genre, grade, aspect ratio, exclusions ("no on-screen text, no music")
SCENE: one-line summary
CHARACTERS: which reference = which character (@character …)
LOCATION: …
FIRST FRAME: {start_frame} – what is visible and where everyone stands (blocking)
Shot 1 (0–4 s): … Hard cut.
Shot 2 (4–8 s): … Hard cut.
OPTICS: lens as field of view (84° wide, 47° normal, 29° short tele, 18° tele), camera height ("40 cm above the asphalt")
CAMERA: one move per shot
PHYSICS: count locks ("exactly one person", "five fingers per hand"), rigid objects ("club shaft stays straight")
LIGHTING: source, direction, time of day
AUDIO: last – "none" or exact lines/SFX
```

- **Uteslutningar fungerar bättre än mer positiv detalj** ("No music, no discernible dialogue", "no on-screen text").
- Vaga övergångar är den vanligaste orsaken till att en sekvens faller isär – skriv "Hard cut." eller beskriv övergången exakt.
- Lås skärmriktning så att personer inte byter sida mellan shots; litet, avsiktligt referensset (50 är ett tak, inte ett mål).
- Enkla klipp: 60–100 ord räcker, viktigast först (kreatörer – senare instruktioner tappas).
- **Dialog:** korta repliker (5–10 ord) inom citattecken, låst kamera under repliken, halvnära rakt framifrån (kreatörer).
  Avsluta med en tystnadsinstruktion för att undvika tvärt slut.
- **Arbetsflöde (Higgsfield hjälpcenter):** börja i2v 720p från en skarp, framåtvänd, välbelyst bild; granska 5–8 s-partiet
  noga; ändra en variabel per körning; rendera samma prompt i 1080p/4K när den sitter.

## Kameravokabulär

`dolly in` · `push in` · `pull back wide` · `truck left/right` · `arc shot` · `orbit` · `crane up` · `handheld follow` ·
`locked-off` · `gyro-rig` · `backpedal` · `whip-pan` · `anamorphic` · `deep focus / shallow focus` – plus linsen som
synfält i grader och kamerahöjd i cm (Higgsfield hjälpcenter + guide).

## Fallgropar → motåtgärder

| Problem | Motåtgärd |
|---|---|
| Karaktären glider (ansikte, kläder) | Samma startbild/referens i varje klipp; visuella ankare (glasögon, kofta, frisyr) i prompten; reference-to-video när det aktiverats. |
| Hackiga klipp mellan genereringar | Första/sista bild-läge: sista bilden i klipp A = första bilden i klipp B (Higgsfield hjälpcenter). |
| Produkten hittas på | Exakt produktfoto i startbilden (gpt-image-2-komposit, D12); låt modellen röra människa/kamera, inte produkten. |
| Extra personer, dubbletter | Antalslås: "exactly one person". |
| Händer | Medelavstånd, inte extrem närbild; "five fingers per hand". |
| Golfklubba/ratt böjs | "the club shaft stays straight and rigid"; vision-QA bildruta för bildruta; riktig film om det inte håller. |
| Oönskat ljud/musik | `generate_audio=false`, eller "AUDIO: none" + explicit "no music". |
| Text i bild | "no on-screen text"; text i HyperFrames. |

## Exempelpromptar för våra recept (ej körda – hypoteser)

1. **FAIV – person vid bil visar grillkit (2.5 i2v, 8 s, 720p, `generate_audio=false`)** – `faiv-product-in-nordic-context` s2
   ```
   GLOBAL STYLE: realistic documentary automotive film, natural Nordic colours, vertical 9:16, no on-screen text, no music.
   SCENE: the owner shows the new grille light on his car.
   FIRST FRAME: {start_frame} – composite of the real person, the real Tesla Model 3 and the exact Lumen grille kit photo; he stands left of the bumper.
   Shot 1 (0–4 s): he crouches next to the front of the car and points at the light bar in the grille. Hard cut.
   Shot 2 (4–8 s): close medium shot, he looks back at the camera and nods once.
   OPTICS: 47° normal lens, camera 90 cm above the ground.
   CAMERA: handheld medium shot, gentle arc to the right in shot 1; locked-off in shot 2.
   PHYSICS: exactly one person, five fingers per hand, the grille and light bar never change shape.
   LIGHTING: blue hour, snow on the ground, car lights off.
   AUDIO: none.
   ```
2. **FAIV – övergång mellan två riktiga bilder (2.5 i2v, 4 s)**: `image_url` = still ur fa-b4 (dagsljus), `end_image_url` = still ur
   fa-b4 (skymning), prompt: `GLOBAL STYLE: realistic. Time-lapse feel: daylight fades to blue hour, clouds drift, nothing else moves. CAMERA: locked-off. AUDIO: none.`
   (Inte ljuset av→på – det är produktbeviset och filmas.)
3. **Golfkuponger – återkommande karaktär på banan (2.5 i2v, 6 s)** – `gk-recurring-character-sketch` s5
   ```
   GLOBAL STYLE: warm natural Scandinavian golf film, vertical 9:16, no on-screen text.
   CHARACTERS: Kenneth – glasses, grey hair, golf pullover (same person as the start frame).
   FIRST FRAME: {start_frame} – Kenneth at address on the tee, seen from behind.
   CAMERA: locked-off behind the golfer, 29° short tele.
   PHYSICS: the club shaft stays straight and rigid, exactly five fingers per hand, the ball leaves the tee cleanly and flies straight.
   LIGHTING: low warm golden-hour sun from the left.
   AUDIO: none.
   ```
4. **Golfkuponger – kontor → banan, match cut (2.5 i2v, 4 s)** – `gk-office-to-course-match-cut` s2: startbild = gpt-image-2-redigering
   av sista kontorsbilden (samma pose, kontoret ersatt av en tee), prompt: `… lifts a golf driver in exactly the motion of the coffee cup in the previous shot. CAMERA: locked-off, identical framing. PHYSICS: club shaft stays straight. AUDIO: none.`
5. **Golfkuponger – reaktion (2.0 i2v, 4 s, 1080p)** – `gk-pov-hr-mail` s2: `… looks up from the phone with a sudden 'oh no' realisation, then freezes. CAMERA: static medium close-up, quick subtle push-in. PHYSICS: natural facial motion, no exaggerated expressions. AUDIO: none.`

## Verifierade exempel

*Inga än.*

## Källor

- Higgsfield – Seedance 2.5 i2v API: https://open.higgsfield.ai/models/bytedance/seedance-2.5/image-to-video/api-reference
- Higgsfield – Seedance 2.0 i2v API: https://open.higgsfield.ai/models/bytedance/seedance-2.0/image-to-video/api-reference
- Higgsfield – hjälpcenter "How do I use Seedance": https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance
- Higgsfield – Seedance 2.5 promptguide: https://higgsfield.ai/blog/seedance-2-5-prompting-guide
- Higgsfield – Seedance 2.5 priser: https://higgsfield.ai/blog/seedance-2-5-pricing-2026
- ByteDance Seed – Seedance 2.0: https://seed.bytedance.com/en/seedance2_0 · 2.5: https://seed.bytedance.com/en/seedance2_5
- fal.ai – Seedance 2.0 promptguide: https://fal.ai/learn/tools/seedance-2-0-prompting-guide
- Kreatörer: https://www.heyuan110.com/posts/ai/2026-07-11-seedance-2-prompt-guide/ · https://www.cutout.pro/learn/?p=2903 · https://videoai.me/blog/seedance-2-0-limitations
- Repo: `docs/2026-09-23-higgsfield-seedance-model-audit.md`, `engine/creative_registry.py`
