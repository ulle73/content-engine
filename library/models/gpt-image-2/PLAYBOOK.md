# gpt-image-2 – playbook (bild, komposit, första/sista bild)

> Fakta kontrollerade 2026-10-09 (OpenAI-dokumentation). **Observera:** OpenAIs bildguide rekommenderar nu
> **GPT Image 2.5** (`gpt-image-2.5-sunburst` för precisa redigeringar, `gpt-image-2.5-flare` för snabb generering)
> för nya integrationer, och gpt-image-2-cookbooken är märkt "archived". gpt-image-2 (snapshot `gpt-image-2-2026-04-21`)
> är fortfarande listad, prissatt och den modell Content Engine är verifierad mot (`engine/creative_registry.py`).
> 2.5 ska utvärderas separat innan den läggs i registret. Inga betalda körningar har gjorts.

## Roll i produktionsmotorn

gpt-image-2 genererar **inte** video. Den bygger stillbilder som video-modellerna animerar:

1. **Komposit-startbild (D12):** riktig person + riktig bil + **exakt produktfoto** från produktkatalogen → en 9:16-bild
   som Kling/Seedance/Veo använder som `image_url`/`start_frame`.
2. **Slutbild/matchbild:** redigera en riktig bild ("change only …") – t.ex. sista kontorsbilden → samma pose på en tee.
3. **Stämningsstills** när ingen video behövs.

Den ska **inte** göra: produktbevis (ljuset tänt/släckt), UI (portal, app, kvitto), text/pris/logga som ska vara exakt.

## Styrkor / svagheter

| | |
|---|---|
| + | Fotorealism och materialkänsla; planerar layout före rendering (kreatörer, Luma). |
| + | Redigering med upp till **16 bilder** in; alla bildinput bearbetas med hög trohet automatiskt (officiellt). |
| + | Bättre text än tidigare generationer; flerspråkig text (japanska, koreanska m.fl. nämnda vid lansering). |
| − | Officiella begränsningar: textplacering/tydlighet, återkommande karaktärer/varumärkeselement kan variera, layoutkänslig komposition svår, upp till ~2 min per komplex prompt. |
| − | Detaljkonsekvens i befintliga varumärkesmärken är opålitlig; kvaliteten sjunker över upprepade redigeringar (kreatörer). |
| − | Svenska tecken (å ä ö): **odokumenterat**. Diakritiska fel rapporterade för andra språk i äldre modeller. |
| − | Händer/ansikten: inget officiellt; cookbooken lovar "robust facial and identity preservation" – otestat av oss. |

## Parametrar

| | |
|---|---|
| Endpoints | `/v1/images/generations`, `/v1/images/edits`, Batch. Inte direkt via Chat Completions/Responses. |
| Bildinput (edits) | Upp till 16 bilder, png/webp/jpg < 50 MB; prompt upp till 32 000 tecken. Mask: PNG < 4 MB, samma mått, gäller första bilden. |
| `input_fidelity` | **Utelämna** för gpt-image-2 (alltid hög). (Cookbookens exempel skickar ändå "high" – följ API-referensen.) |
| Storlek | `auto`, 1024x1024, 1536x1024, 1024x1536, eller egen `BxH`: multiplar av 16, förhållande 1:3–3:1, 655 360–8 294 400 px, max 3840x2160; > 2560x1440 "experimentellt". 9:16: t.ex. **1152x2048** eller 1440x2560 (giltiga enligt reglerna, otestade). |
| Kvalitet | `low`, `medium`, `high`, `auto`. |
| Bakgrund | `transparent` (preview för gpt-image-2, kräver png/webp), `opaque`, `auto`. |
| Utdata | png (default), jpeg, webp; `output_compression` 0–100 (jpeg/webp); `n` 1–10. |
| **Content Engine i dag** | Registret tillåter bara 1024x1024, 1024x1536, 1536x1024 och adaptern tar **en** källbild. Flerbildskomposit och äkta 9:16 (1152x2048) kräver en adapterändring. |

**Pris (officiellt, per bild, bara utdata – referensbilder kostar input-tokens):**

| Kvalitet | Kvadrat | Stående | Liggande |
|---|---|---|---|
| low | 0,006 USD | 0,005 | 0,005 |
| medium | 0,053 | 0,041 | 0,041 |
| high | 0,211 | 0,165 | 0,165 |

Tokenpris: bildinput 8 USD/M, bildutdata 30 USD/M, textinput 5 USD/M; Batch halva priset
([priser](https://developers.openai.com/api/docs/pricing), [bildguide](https://developers.openai.com/api/docs/guides/image-generation)).

## Promptformat

OpenAIs struktur ([promptguide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)):
**scen/bakgrund → subjekt → nyckeldetaljer → begränsningar**, med syfte ("start frame for a vertical social video").
Märkta segment/radbrytningar hellre än smart syntax. Matchar registrets `prompt_sections`
(USER_INTENT, VISUAL_DIRECTION, FORMAT, PRESERVE, AVOID …).

```
Image 1: exact product photo of {product} – preserve exactly.
Image 2: reference photo of the person. Image 3: reference photo of the {car_model}.

Intent: photorealistic real photograph, start frame for a vertical 9:16 social video.
Scene: {plats, tid på dygnet, väder}.
Subject: {person från Image 2} {handling, kroppsinramning, blick, var händerna är}.
Product: reproduce the product from Image 1 exactly in the front grille of the car from Image 3 –
same shape, LED layout, colours and logo; do not redesign.
Integration: match lighting direction, colour temperature, perspective, scale and contact shadows.
Motion space: leave headroom and empty space {vänster/höger} for camera movement.
Avoid: extra text, added logos, watermark, licence plates.
```

- **Redigeringar:** "change only X" + "keep everything else the same" – upprepa bevara-listan i varje iteration;
  för kirurgiska ändringar förbjud även ändrad mättnad, kontrast, layout, etiketter och kameravinkel.
- **Flera bilder:** referera med index och roll ("Image 1: product…, Image 2: style reference") och säg exakt hur de samverkar.
- **Fotorealism:** "photorealistic"/"real photograph", be om verklig textur (porer, slitet tyg), undvik ord som antyder studiopolish.
  Objektiv/bländare tolkas löst – använd för helhetslook.
- **Text (om absolut nödvändigt):** citerad eller VERSALER, typsnitt/storlek/färg/placering, "EXACT, verbatim, no extra characters",
  medium/high kvalitet. **Vår regel: all text läggs i HyperFrames, inte i bilden.**
- **Iteration:** ren basprompt, en ändring per uppföljning; utforska i `low`, slutför i `medium`/`high`.

## Startbild för video – tips

- Generera i **målformatet** (9:16) från början – i2v behåller bildens inramning.
- Lämna plats för rörelse (motivet fyller inte bilden, luft för kameraåkning).
- Skarp, välbelyst, ren bild minskar flimmer; gör 3–4 varianter och välj den med tydligast rörelselogik.
- Slutbild: redigera startbilden med "change only [pose/kameraposition]" + full bevara-lista (härlett, inte dokumenterat av OpenAI).

## Fallgropar → motåtgärder

| Problem | Motåtgärd |
|---|---|
| Produkten ritas om (form, LED, logga) | Produktfoto som Image 1 med "preserve exactly"; få redigeringsvarv; håll loggytan ren och lägg riktig logga/packshot i efterhand. |
| Ljus/perspektiv matchar inte i komposit | Explicit "match lighting, perspective, scale, shadows, colour temperature"; gradera i efterhand. |
| Drift över iterationer | Börja om från originalbilden i stället för att redigera redigeringar; upprepa bevara-listan. |
| å ä ö fel | Ingen text i bilden; text i HyperFrames. |
| Karaktär varierar mellan bilder | Samma referensbild som input varje gång; beskriv ankare (glasögon, kofta). |
| Fel bildformat (2:3 i stället för 9:16) | Välj 1152x2048 när adaptern stöder det; annars 1024x1536 + beskär. |

## Exempelpromptar för våra recept (ej körda – hypoteser)

1. **FAIV – komposit-startbild: person vid Tesla med exakt grillkit** – `faiv-product-in-nordic-context` s1/s2
   ```
   Image 1: exact product photo of the Lumen grille light kit for Tesla Model 3 – preserve exactly.
   Image 2: photo of the person (consenting customer). Image 3: photo of the customer's white Tesla Model 3.
   Intent: photorealistic real photograph, start frame for a vertical 9:16 social video.
   Scene: snowy forest road in Sweden at blue hour, pine trees, light snowfall.
   Subject: the person from Image 2 stands left of the car's front bumper, full body visible, looking at the grille, relaxed.
   Product: the kit from Image 1 mounted in the front of the car from Image 3, exactly the same shape, LED layout and logo. Lights off.
   Integration: match lighting direction, colour temperature, perspective, scale and contact shadows.
   Motion space: leave empty space on the right for a slow camera arc.
   Avoid: text, added logos, watermark, licence plates.
   ```
2. **FAIV – ren produktbild för Kling-makro** – `faiv-dark-to-light-reveal` s5: `Image 1: exact product photo – preserve exactly. Change only the background: dark studio, subtle reflections on a black surface, product centred with space above. Keep the product's shape, LED layout, colours and logo identical. Vertical 9:16.`
3. **Golfkuponger – matchbild kontor → tee** – `gk-office-to-course-match-cut` s2
   ```
   Image 1: last frame of the office shot. Change only the environment and the object in the hand:
   the office becomes the first tee of a Swedish parkland course in soft morning light, and the coffee cup becomes a golf driver held the same way.
   Keep the person, pose, clothing, framing, camera angle and lighting direction exactly the same.
   ```
4. **Golfkuponger – karaktärsark för återkommande karaktär** – `gk-recurring-character-sketch`: `Photorealistic character reference sheet of the person in Image 1: front, three-quarter and profile views on a neutral grey background, same glasses, beige cardigan, grey hair. Even soft light. No text.` (Används som referens för Seedance/Veo; personen har gett samtycke.)
5. **Golfkuponger – stämningsstill för nedräkning** – `gk-deadline-31-dec` s4: `Photorealistic photograph of a snow-covered golf green in Sweden in December, flag in the hole, grey winter daylight, empty, vertical composition with calm space in the upper third. No text, no logos.`

## Verifierade exempel

*Inga än.*

## Källor

- OpenAI – gpt-image-2: https://developers.openai.com/api/docs/models/gpt-image-2
- OpenAI – bildgenereringsguide: https://developers.openai.com/api/docs/guides/image-generation
- OpenAI – Images edit API: https://developers.openai.com/api/reference/python/resources/images/methods/edit
- OpenAI – promptguide (cookbook): https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- OpenAI – priser: https://developers.openai.com/api/docs/pricing
- Kreatörer – Luma gpt-image-2-guide: https://lumalabs.ai/learning-center/articles/gpt-image-2-complete-guide
- Kreatörer – bild → video-arbetsflöde: https://www.nemovideo.com/blog/gpt-image-2-to-video-workflow
- Repo: `engine/creative_registry.py` (gpt-image-2-profilen)
