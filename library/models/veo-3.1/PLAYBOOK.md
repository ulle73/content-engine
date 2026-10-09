# Veo 3.1 – playbook (Veo 3.1 · Fast · Lite)

> Fakta kontrollerade 2026-10-09 (Google-dokumentation). **Veo 3.1 finns inte i Higgsfields publika API-katalog**
> (open.higgsfield.ai) och inte i Content Engines modellregister – den går bara att köra via Gemini API/Vertex AI
> (kräver ny integration och Google-faktura) eller manuellt i Higgsfields webbapp. Gemini API-översikten
> rekommenderar nu "Gemini Omni Flash" som standard-videomodell men pekar fortfarande på Veo 3.1 för förlängning
> och slutbild. Inga betalda körningar har gjorts.

## När Veo 3.1

- **Tal och läppsynk i bild** – dialog, SFX och ambiens genereras tillsammans med bilden (alltid på i Gemini API).
- **Realism, fysik och promptföljsamhet** – Google uppger att modellen leder människobedömningar på dessa.
- **Flera shots i ett 8 s-klipp** med tidsstämplar.
- Inte förstaval för: svensk dialog utan provkörning (odokumenterat), produkter med fina detaljer, långa sammanhängande klipp
  (4/6/8 s; förlängning i 7 s-steg i 720p med kvalitetsavvägning).

## Styrkor / svagheter

| | |
|---|---|
| + | Native ljud: dialog, SFX, ambiens, "bättre synkat med videoinnehållet" ([DeepMind](https://deepmind.google/models/veo/)). |
| + | Referensbilder ("ingredients"): upp till 3 bilder på person, karaktär eller produkt (3.1 och Fast). |
| + | Första + sista bild (`image` + `lastFrame`), nativ 9:16 sedan 2026-01-13. |
| − | Google: naturligt och konsekvent tal, särskilt i korta segment, är "an area of active development". |
| − | **Språk:** "English (EN) is fully supported, but other languages have not been evaluated" (Gemini API). Vertex: promptspråk engelska. **Svenska är odokumenterat.** |
| − | Kreatörer: talet är engelskcentrerat; Kling 3.0 uppges bättre på flerspråkig läppsynk; kinesisk dialog < 30 % lyckade. Inga svenska tester hittade. |
| − | Inbrända undertexter när det finns dialog (kreatörer) – kan inte tas bort i efterhand. |
| − | Referensbilder är "ett starkt förslag, ingen garanti"; logga som referens blev bättre men fortfarande inexakt (kreatörer). |
| − | Blockerar ibland genereringar av ljudsäkerhetsskäl (ingen debitering då). |

## Parametrar (Gemini API / Vertex)

| | |
|---|---|
| Modell-id | Gemini API: `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview`. Vertex: `veo-3.1-generate-001`, `veo-3.1-fast-generate-001` (GA 2025-11-17), Lite preview. |
| Längd | 4, 6 eller 8 s. **8 s krävs** för förlängning, referensbilder, 1080p och 4K. |
| Upplösning | 720p (default), 1080p, 4K (8 s). Lite: ingen 4K. Fast + 4K: motstridigt (Gemini API ja, Vertex nej). 4K kan vara uppskalning. |
| Format | 16:9 (default), 9:16. |
| Bild | image-to-video (bilden = första bild), `lastFrame` (kräver `image`), upp till 3 referensbilder (inte Lite). |
| Förlängning | +7 s per steg, max 20 steg (148 s), bara 720p, bara Veo-genererad input; rösten följer bara med om det pratas i sista sekunden. |
| Övrigt | 24 fps, prompt max 1 024 tokens, 1 video/anrop (Vertex upp till 4), latens 11 s–6 min, lagras 2 dagar, SynthID-vattenmärke. `negativePrompt` dokumenterat i Vertex; för Gemini API overifierat. `seed` för 3.1 overifierat. |
| EU | `personGeneration`: i EU/UK/CH bara `allow_adult` – gäller oss i Sverige. |

**Pris (Gemini API, betald nivå, per sekund video med ljud, sidan uppdaterad 2026-10-07, läst 2026-10-09):**
Veo 3.1 0,40 USD (720p/1080p) / 0,60 (4K) · Fast 0,10 / 0,12 / 0,30 · Lite 0,05 / 0,08.
Ett 8 s Fast-klipp i 1080p ≈ 0,96 USD; Veo 3.1 ≈ 3,20 USD. Ingen gratisnivå. [Källa](https://ai.google.dev/gemini-api/docs/pricing).

## Promptformat

**Googles formel:** `[Cinematografi] + [Subjekt] + [Handling] + [Kontext] + [Stil & ambiens]`
([Cloud-bloggen](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)).

**Ljud – tre separata spår, egna meningar:**
- Dialog: `A woman says, "We have to leave now."` (Gemini API: citattecken för exakt tal). Äldre Vertex-guide: kolon utan citattecken.
- `SFX: thunder cracks in the distance`
- `Ambient noise: the quiet hum of an office`
- Talarattribution vid flera personer: `He looks up at her and says in a weary voice, "…"` / `she replies, "…"`.

**Tidsstämplar för flera shots i ett klipp:** `[00:00-00:02] Medium shot … [00:02-00:04] Reverse shot … SFX: …`.

**Negativa:** beskriv hellre det du vill ha ("an empty office with no people"). I Vertex `negativePrompt`: substantiv
("subtitles, captions, on-screen text"), inte "no …".

**Undvika inbrända undertexter (kreatörer, "inte idiotsäkert"):** skriv "(no subtitles)" direkt efter repliken; undvik
apostrofer/sammandragningar; testa kolon-formen mot citattecken; lägg "subtitles, captions, on-screen text" i negativ prompt (Vertex).
Säkraste vägen: generera bild + ambiens/SFX **utan tal**, lägg svensk röst (egen inspelning) och captions i HyperFrames.

## Kameravokabulär (officiell)

Rörelse: `dolly`, `tracking`, `crane`, `aerial`, `slow pan`, `POV`, `static`, `tilt`, `truck`, `pedestal`, `zoom`,
`handheld`, `whip pan`, `smooth 180-degree arc shot`. Komposition: `wide`, `close-up`, `extreme close-up`, `low angle`,
`two-shot`, `eye-level`, `high-angle`, `bird's-eye`, `worm's-eye`, `Dutch`, `over-the-shoulder`. Lins: `shallow depth of field`,
`wide-angle`, `telephoto`, `macro`, `rack focus`, `soft focus`, `dolly zoom`. Tempo: `slow-motion`, `time-lapse`.
Ordet `portrait` ger mer ansiktsdetalj (Gemini API). Vertex: "vissa avancerade vinklar/linser stöds inte officiellt".

## Fallgropar → motåtgärder

| Problem | Motåtgärd |
|---|---|
| Svensk replik blir fel/osynkad | Provkör 3–5 Fast-klipp (720p, 8 s ≈ 0,80 USD st) innan ett recept bygger på det; annars tyst klipp + egen svensk röst. |
| Inbrända undertexter | Se ovan; i värsta fall generera utan tal. |
| Identitet glider mellan klipp | Samma 1–3 referensbilder ("ingredients") i varje klipp; samma startbild; få men stabila beskrivningar. |
| Produkt/logga inexakt | Lås med första bild/referensbild från exakt produktfoto (D12); riktig logga i efterhand. |
| Rumsliga kamerainstruktioner tolkas olika | En rörelse per shot; enkla ord. |
| Förlängda klipp tappar kvalitet | Planera 8 s-klipp och klipp ihop i HyperFrames i stället. |

## Exempelpromptar för våra recept (ej körda – hypoteser)

1. **Golfkuponger – karaktären presenterar sig (8 s, 9:16)** – `gk-recurring-character-sketch` s1
   ```
   Medium close-up, static camera at eye level. A Swedish office worker in his 50s with glasses and a beige cardigan
   stands in a bright open-plan office and looks straight into the camera with a completely deadpan face.
   He says in Swedish: "Jag har friskvårdsbidrag kvar. Igen." (no subtitles)
   Ambient noise: quiet office room tone, distant keyboard typing. No music. No on-screen text.
   ```
2. **Golfkuponger – tips-presentatör (8 s)** – `gk-friskvard-tips` s1
   ```
   Medium shot, handheld phone-style framing. A friendly Swedish woman in her 30s in a bright office kitchen points up
   and says to the camera in Swedish: "Tre saker om friskvårdsbidraget som ingen berättar." (no subtitles)
   Ambient noise: quiet office, a coffee machine in the background. No music. No on-screen text.
   ```
3. **Golfkuponger – kontor → golf med tidsstämplar (8 s, utan tal)**
   ```
   [00:00-00:03] Medium shot, static: a man at his desk closes his laptop and exhales. Ambient noise: office hum.
   [00:03-00:08] Wide shot, slow dolly-in: the same man in a golf pullover walks onto the first tee of a Swedish
   parkland course in soft morning mist. SFX: birds, a distant club strike. No music. No on-screen text.
   ```
4. **FAIV – kunden vid bilen (8 s, referensbild = exakt produktfoto + kundens bil)**
   ```
   Medium shot at bumper height, slow 90-degree arc. A Swedish man in his 40s in a winter jacket stands next to his
   Volvo XC60 parked on a snowy forest road at blue hour and pats the hood. He says: "Det bara fungerar." (no subtitles)
   SFX: snow crunching underfoot. Ambient noise: quiet forest, light wind. The grille stays exactly as in the reference image.
   ```
   Ljuset av→på genereras aldrig – det filmas (produktbevis). Repliken är tagline-ton, inte ett faktapåstående.
5. **FAIV – stämning utan tal (8 s, Fast)**: `Aerial shot, slow push forward over a dark winter road through a Swedish pine forest at dusk. Ambient noise: wind in the trees, a distant engine approaching. No music. No on-screen text.`

## Verifierade exempel

*Inga än.* Första uppgiften: provkör svensk replik (exempel 1) i Fast 720p och dokumentera här.

## Källor

- Gemini API – Veo: https://ai.google.dev/gemini-api/docs/veo · video-översikt: https://ai.google.dev/gemini-api/docs/video
- Gemini API – priser: https://ai.google.dev/gemini-api/docs/pricing
- Google Cloud – Ultimate prompting guide for Veo 3.1: https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
- Vertex AI – Veo-promptguide: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide
- Vertex AI – Veo 3.1: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate
- Google DeepMind – Veo: https://deepmind.google/models/veo/
- Google – Veo 3.1-uppdatering (nativ 9:16): https://blog.google/innovation-and-ai/technology/developers-tools/veo-3-1-gemini-api/
- Higgsfield – Veo 3.1 i appen: https://higgsfield.ai/blog/How-to-Use-Google-Veo-3.1-Complete-Guide-for-the-New-Model
- Kreatörer (undertexter): https://www.kapwing.com/resources/how-to-add-accurate-subtitles-to-veo-3-google-gemini-videos/
- Kreatörer (ljudmodeller jämförda): https://www.atlascloud.ai/blog/guides/ai-video-models-native-audio-compared
