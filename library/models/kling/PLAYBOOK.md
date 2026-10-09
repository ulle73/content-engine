# Kling – playbook (2.5 Turbo Pro · 2.6 Pro · 3.0 Std/Pro/4K)

> Fakta kontrollerade 2026-10-09. "Officiellt" = Kling eller Higgsfields API-referens. "Kreatörer" = guider från
> tredje part (hypoteser att testa). Inga betalda körningar har gjorts för den här playbooken – avsnittet
> *Verifierade exempel* är tomt tills ägaren godkänt ett resultat.

## När Kling

- **Produkt i rörelse från exakt startbild** (grillkit på bil, makro av lampa som tänds): bevarar startbildens
  komposition väl i image-to-video. Kling 3.0 har dessutom slutbild (`last_image_url`) och Elements.
- **Miljö/b-roll** (skogsväg, bana i morgondimma, verkstad i kvällsljus): 2.5 Turbo Pro är billigast av de starka.
- **Längre sammanhängande tagning** (3.0: upp till 15 s, "one continuous long take") och **multi-shot** i en generering (3.0).
- Inte förstaval för: tal på svenska, närbilder på händer som hanterar små föremål, scener där läsbar text ska stå still.

## Styrkor / svagheter

| | |
|---|---|
| + | Följer namngivna kamerarörelser; fysik i vätskor/ljus/partiklar (kreatörer: atlabs, VEED). |
| + | 3.0: multi-shot, Elements för identitet/produkt, behåller text/logga från källbilden (officiellt, Kling 3.0-guiden). |
| + | 2.5 Turbo: snabb, bevarar startbildens komposition (kreatörer). |
| − | "Inte känslig för siffror" – exakta antal misslyckas; komplex fysik (studs, kast) är svårt (officiellt, Kling T2V-guide). |
| − | Liten text och fina produktdetaljer förändras under rörelse; förpackningstext, handinteraktion och flera produkter är svagt (kreatörer). |
| − | Överlastad prompt → hackig, stressad rörelse (kreatörer). |
| − | 2.5 Turbo: mjukare detaljer på avstånd, max 10 s (kreatörer). |
| − | 3.0 tal: bara kinesiska, engelska, japanska, koreanska, spanska – övriga språk översätts till engelska → **svensk dialog fungerar inte** (officiellt). |

## Parametrar (Higgsfield REST – det vi faktiskt anropar)

| Modell (endpoint) | Längd | Slutbild | Ljud | Övrigt | Källa |
|---|---|---|---|---|---|
| `kling-video/v2.5-turbo/pro/{text,image}-to-video` | 5 eller 10 s | **nej** | nej | `cfg_scale` 0–1 (0,5), `negative_prompt`; inget `aspect_ratio` – formatet följer startbilden / prompten | [Higgsfield i2v](https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-image-to-video) |
| `kling-video/v2.6/pro/…` | 5 eller 10 s | nej | `sound` | Kling: 16:9, 1:1, 9:16; röst bara kinesiska/engelska | [Kling 2.6-guide](https://kling.ai/quickstart/klingai-video-26-audio-user-guide) |
| `kling-video/v3.0/{std,pro,4k}/…` | 3–15 s | `last_image_url` | `sound` "on"/"off", **default on** | `cfg_scale`, `multi_shots`, `multi_prompt[]`, `elements[]` (fälten är inte beskrivna hos Higgsfield); ingen `negative_prompt` listad | [Higgsfield 3.0 Pro i2v](https://open.higgsfield.ai/models/kling-video/v3.0/pro/image-to-video/api-reference) |

- Kontraktet per läge (fält, längder) finns i `engine/higgsfield_video_profiles.json` / `engine/creative_registry.py` – det är sanningen för koden.
- **Pris:** registrets planeringsvärden (konservativa, inte offert): 2.6 Pro ≈ 0,070 USD/s, 3.0 Std ≈ 0,084, 3.0 Pro ≈ 0,112, 3.0 4K ≈ 0,42 USD/s.
  Higgsfields blogg: 15 s 3.0 = 30/37,5/90 krediter (720p/1080p/4K) ([källa](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation)).
  2.5 Turbo Pro: **pris okänt** i dokumentationen. Kontopris = `/estimate/` före varje körning.
- **Okänt/overifierat:** exakt form på `multi_prompt`/`elements` hos Higgsfield (fal.ai: `{prompt, duration}` resp. element-bilder,
  refereras `@Element1`); maxantal shots (5 enligt Higgsfield, 6 enligt fal/Morphic, ingen gräns officiellt); nativ 4K vs uppskalning.

## Promptformat

**Officiell formel (Kling):** `Subjekt (beskrivning) + Subjektets rörelse + Scen` + valfritt `(Kameraspråk + Ljus + Atmosfär)`.
Enkla ord; handlingen ska rymmas i 5–10 s ([Kling T2V-guide](https://kling.ai/quickstart/text-to-video-prompt-guide)).

**Image-to-video (vårt normalfall):** beskriv **vad som rör sig, vad som står still och hur kameran rör sig** – inte hur
saker ser ut (det gör startbilden). Avsluta rörelsen med ett slut-tillstånd ("…then settles", "…and holds").

```
Start frame: {product_image}.
[Vad som händer, ett verb-led]. [Vad som är stilla: "the car and grille stay exactly as in the start frame"].
Camera: [EN rörelse]. Lighting: [ljuskälla + riktning]. Vertical 9:16.
Negative: warped text, morphing, extra lights, changed logo, licence plate, blur.
```

**3.0 multi-shot:** `Shot 1, …` `Shot 2, …` (Custom Multi-Shot = fasta längder per shot). Definiera subjekt/element
först och upprepa samma ord i varje shot; tagga element i varje shot där det syns; en handling + en kamerarörelse per shot
(officiellt + Higgsfield-bloggen). Tidsangivelse fungerar: "At the 4th second, …".

**Start + slutbild:** två liknande bilder med samma tema; stora skillnader ger ett klipp i stället för en övergång.
Övergångar under 5 s blir mjukast ([Kling start/end](https://kling.ai/quickstart/ai-video-start-end-frames)).
Vid vid startbild + tele-slutbild blir modellen förvirrad (Higgsfield-snippet, sidan 404 – overifierat).

## Kameravokabulär som fungerar

`slow push-in` · `dolly-in / dolly-out` · `tracking shot` / `lateral track` · `low-angle tracking` · `orbit` / `orbital pan` ·
`crane down / crane up` · `drone follow` / `aerial push forward` · `macro close-up` · `POV` · `whip-pan` ·
`static wide shot` · `handheld with subtle drift` · `gradual reveal` · `one continuous long take` (3.0).
Utan kamerainstruktion blir det oftast statiskt. Kreatörer är oense om aggressiva rörelser på 5 s – börja lugnt.

## Fallgropar → motåtgärder

| Problem | Motåtgärd |
|---|---|
| Produkten "morfar", loggan förvanskas, fler LED än i verkligheten | Startbild (och slutbild i 3.0) = exakt produktfoto (D12); låst eller långsam kamera; negativ prompt (2.5); Element med produktbilder (3.0); riktig logga i efterhand. |
| Hackig/stressad rörelse | En handling per klipp; kedja klipp genom att använda förra klippets sista bild som nästa startbild. |
| Text i bild blir nonsens | Ingen text i prompten; skyltar utan läsbar text; all text i HyperFrames. |
| Händer/fingrar fel | Undvik närbild på händer; medelavstånd; räkna med omtag. |
| Ljud kommer med (3.0/2.6) | Sätt `sound: "off"` explicit. |
| Ljusbilden blir "AI-glow" | Använd aldrig AI för produktbeviset (ljuset av→på, räckvidd). Bara stämning/miljö. |
| Svensk replik | Inte i Kling – använd Veo 3.1 (provkör) eller egen röst i efterhand. |

## Exempelpromptar för våra recept (ej körda – hypoteser)

1. **FAIV grillkit-reveal på natten (i2v, 3.0 Pro, 5 s, sound off)** – `faiv-installed-and-done` s5
   ```
   Start frame: real photo of the installed Lumen grille light kit on this Volvo XC60, parked in a dark workshop.
   The grille light switches on and its white light gently fills the room, then holds steady.
   The car, grille and light layout stay exactly as in the start frame.
   Camera: slow dolly-out at bumper height. Lighting: warm practical lights, then the product's own white light.
   Vertical 9:16.
   ```
   Slutbild (`last_image_url`): riktigt foto av samma bil med ljuset tänt – modellen får bara tolka övergången.
2. **FAIV produktmakro (i2v, 2.5 Turbo Pro, 5 s, negativ prompt)** – `faiv-dark-to-light-reveal` s5
   ```
   Extreme macro of the light bar in the grille; the LEDs ignite left to right and a soft bloom builds, then settles.
   Camera: very slow dolly-in, shallow depth of field. Lighting: dark studio, only the product's own light.
   ```
   `negative_prompt`: `warped text, morphing, extra LEDs, changed logo, blur, distortion`
3. **FAIV vintermiljö (t2v, 2.5 Turbo Pro, 5 s)** – `faiv-winter-mood` s1
   ```
   Empty winter road through a dark Swedish pine forest at dusk, fresh snow, no cars, no people.
   Camera: slow aerial drone push forward along the road, slight descent. Lighting: deep blue dusk. Cinematic, realistic.
   ```
4. **Golfkuponger kontor → golf (i2v, 3.0 Std, 5 s)** – `gk-office-to-course-match-cut` s6
   ```
   Start frame: {start_frame}. A person in casual golf clothes steps onto the first tee of a Swedish golf course
   in the morning, pine trees and soft mist behind. Camera: follow from behind at walking pace, steady gimbal.
   Lighting: soft morning sun. Vertical 9:16.
   ```
5. **Golfkuponger sketch, multi-shot (3.0 Pro, 10 s, Custom Multi-Shot)** – variant av `gk-recurring-character-sketch`
   ```
   @Element1 is a Swedish office worker in his 50s with glasses and a beige cardigan.
   Shot 1 (4 s): @Element1 sits at his desk in an open-plan office and sighs at a full calendar on the screen. Static medium shot.
   Shot 2 (6 s): @Element1, now in a golf pullover, tees up on a Swedish parkland course at golden hour and smiles. Slow push-in.
   ```
   Element byggs av 2–4 referensbilder på skådisen (samtycke). Ingen dialog (svenska stöds inte).

## Verifierade exempel

*Inga än.* Lägg till prompt + inställningar + länk till resultat + ägarens betyg när en körning godkänts.

## Källor

- Higgsfield – Kling 2.5 Turbo Pro i2v: https://docs.higgsfield.ai/docs/models/kling-2-5-turbo/pro-image-to-video
- Higgsfield – Kling 3.0 Pro i2v: https://open.higgsfield.ai/models/kling-video/v3.0/pro/image-to-video/api-reference
- Higgsfield – Kling 3.0-guide: https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation
- Kling 3.0 användarguide: https://kling.ai/quickstart/klingai-video-3-model-user-guide
- Kling 2.6 audio-guide: https://kling.ai/quickstart/klingai-video-26-audio-user-guide
- Kling text-to-video-promptguide: https://kling.ai/quickstart/text-to-video-prompt-guide
- Kling start/slutbild: https://kling.ai/quickstart/ai-video-start-end-frames
- Kling kamerakontroll: https://kling.ai/quickstart/ai-camera-control-guide
- fal.ai – Kling 3.0 Pro i2v API: https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/api
- fal.ai – Kling 3.0 promptguide: https://blog.fal.ai/kling-3-0-prompting-guide/
- Atlabs – Kling 2.5 Turbo promptguide: https://www.atlabs.ai/blog/kling-2-5-turbo-prompting-guide
- VEED – Kling 2.5 Turbo-promptar: https://www.veed.io/learn/kling-2-5-turbo-prompts
- Morphic – Kling 3.0-guide: https://morphic.com/resources/how-to/kling-3.0-guide
- Repo: `docs/2026-10-03-model-catalog.md`, `engine/higgsfield_video_profiles.json`
