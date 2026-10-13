# Model playbooks – vilken AI-modell per scen (D10)

> Modell väljs **per scen, inte per film** (MASTERPLAN D10). Den här tabellen är ett utgångsläge för
> `creative_director` och för den som bygger ett recept – inte en spärr. **Sanningen om vad som faktiskt är
> tillgängligt och verifierat är modellregistret** (`engine/creative_registry.py` + `engine/higgsfield_video_profiles.json`);
> kostnaden avgörs alltid av leverantörens `/estimate/` före betald körning, aldrig av siffrorna här.
>
> All AI-video är **valfri och betald** (inte finansierad än). Varje recept i `library/recipes/` fungerar med riktigt
> material från `docs/FILMLISTA.md`; scener som *kan* uppgraderas har `ai_upgrade` i `recipe.json`.

| Playbook | Modeller | I registret? |
|---|---|---|
| [`kling/PLAYBOOK.md`](kling/PLAYBOOK.md) | Kling 2.5 Turbo Pro, 2.6 Pro, 3.0 Std/Pro/4K (Higgsfield) | Ja – alla fem |
| [`seedance/PLAYBOOK.md`](seedance/PLAYBOOK.md) | Seedance 2.0, 2.5 (Higgsfield) | Ja – båda |
| [`veo-3.1/PLAYBOOK.md`](veo-3.1/PLAYBOOK.md) | Google Veo 3.1 / Fast / Lite | **Nej** – inte i Higgsfields API; kräver Gemini API/Vertex-integration |
| [`gpt-image-2/PLAYBOOK.md`](gpt-image-2/PLAYBOOK.md) | OpenAI gpt-image-2 (bild, komposit, första/sista bild) | Ja |

## Routning: scentyp → modell

| Scentyp | Förstahand | Alternativ | Varför / villkor |
|---|---|---|---|
| **Produktbevis** (ljuset tänds, före/efter, räckvidd) | **Riktig film – aldrig AI** | – | Ljusbilden är ett produktpåstående; AI-simulerad = vilseledande reklam. |
| **Produkt i rörelse** (grillkit på bil, makro av lampa) | Kling 3.0 Pro i2v med start- (+ slut-) bild = exakt produktfoto | Seedance 2.5 i2v med `end_image_url` | D12: produkten kommer från riktigt foto; modellen får bara röra kamera/ljus/miljö. |
| **Människa / karaktär** (reaktion, person vid bil, sketch) | Seedance 2.5 (Elements/@character-referens) | Kling 3.0 med Elements | Seedance håller identitet och mänsklig rörelse bäst enligt Higgsfields egna tester; referensbild > textbeskrivning. |
| **Tal / läppsynk i bild** | Veo 3.1 (native dialog) | Seedance 2.5 (native ljud) · eller tyst klipp + egen svensk röst i efterhand | **Svenska är odokumenterat** hos Veo, Kling (översätts till engelska) och osäkert hos Seedance – provkör innan en film bygger på det. |
| **Miljö / b-roll** (skogsväg, bana i dimma, verkstad, norrsken) | Kling 2.5 Turbo Pro (5/10 s) | Kling 3.0 Std, Wan 3.0 (billigast i registret) | Billigaste modell som klarar scenen. Inga människor eller text i bild. |
| **Cinemagraph av riktigt foto** (snö som faller kring parkerad bil) | Kling 3.0 Std i2v | Seedance 2.0 i2v | Rör bara miljön; låst kamera. |
| **Matchklipp/övergång mellan två riktiga bilder** | Seedance 2.5 i2v (`image_url` + `end_image_url`) | Kling 3.0 (`last_image_url`) | Första/sista bild från riktiga klipp; korta (≤ 5 s) övergångar blir mjukast. |
| **Första/sista bild, komposit** (person + bil + exakt produkt) | gpt-image-2 (edits, flera bilder) | – | Bygg startbilden med det exakta produktfotot; video-modellen animerar sedan. |
| **Rollbyte på eget grovklipp** (kollega vid bilen → återkommande karaktär, personal i sketch → seriefigur; behåll kamera, rörelse, tajming och vårt eget ljud) | **Genjutsu** (verktygslådan, skill `tool-genjutsu`: djupkarta + SAM 3-mask eller face mesh → Seedance 2.5 Edit via Enhancor) | Seedance 2.5 med karaktärsreferens från noll | Bara på material vi har rätt till – aldrig på någon annans annons eller för att efterlikna en verklig person. Körs lokalt (WSL2) av Claude Code/Codex; inte via ChatGPT/MCP än. Utkast först, 1080p efter godkännande. |
| **Text, logga, pris, UI** | **HyperFrames (kod)** – aldrig genererat | – | Alla modeller förvanskar liten text och loggor; portal/app-UI är alltid riktiga skärminspelningar. |
| **Effekter, grafik, övergångar** | HyperFrames-biblioteket (`type=effect/transition/caption`) | – | Gratis, deterministiskt, redigerbart. |

## Gemensamma regler (alla modeller)

1. **Exakt produkt (D12):** produkt, logga, app-skärm kommer från riktiga foton/inspelningar som start-/slutbild eller
   komposit. Modellen ritar aldrig produkten fritt. Riktig logga läggs på i efterhand.
2. **En handling och en kamerarörelse per klipp/shot.** Överlastade promptar ger hackig rörelse i alla modeller.
3. **Ljud av som standard:** Seedance (`generate_audio`) och Kling 3.0/2.6 (`sound`) har ljud **på** som default –
   sätt det explicit. Musik, SFX och röst läggs i klippet (−14 LUFS).
4. **Ingen text i genererad bild:** skriv "no on-screen text" / negativ prompt; all text i HyperFrames.
5. **Vision-QA per klipp** (MASTERPLAN §4b steg 6): händer, ansikte, produktgeometri, logga, klubbor/ratt som böjs,
   inbränd text. Räkna med 3–5 försök per användbart klipp.
6. **Människor:** riktiga personer bara med samtycke; aldrig AI-genererade "kunder" i testimonials.
7. **Billig utkastkörning först** (480p/720p, kort längd), samma prompt i högre upplösning när den sitter.

## Underhåll

Datum på varje fakta. När en modell ändras: uppdatera playbooken **och** registret (`docs/2026-10-03-model-catalog.md`
beskriver hur). Lärdomar från riktiga körningar (prompt + resultat + betyg) läggs under "Verifierade exempel" i
respektive playbook – i dag finns inga, eftersom inga betalda körningar gjorts för dessa recept.
