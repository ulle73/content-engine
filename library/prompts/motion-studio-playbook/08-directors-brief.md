# Regissörsbrief för längre filmer

**Vad:** en brief att fylla i innan någon kod skrivs för en film på 30 s–5 min (berättelse,
explainer, musikvideo, varumärkesfilm). Den låser idé, referenser, verktyg, karaktärer, tidslinje,
exakt text, grindar och leverabler – så att modellen kan jobba länge utan att tappa riktningen.
**När:** allt längre än en annons, och alltid när flera agenter/kapitel ska bygga parallellt
(se `11-parallel-chapters.md`).

## Mall (fyll i, lämna "–" där något inte gäller)

```markdown
# [Arbetstitel] – regissörsbrief

## Logline
En mening: vem/vad, vad som händer, varför man bryr sig. [ ]
Känsla i tre ord: [ ]   Publik: [ ]   Var den visas: [ ]

## Format
Längd [ ] s · format [9:16 först, sedan 1:1/16:9] · [30] fps · språk [svenska] · undertexter [ja/nej]

## Referenser – och vad vi tar från dem
| Referens (länk/fil) | Vi tar | Vi tar INTE |
|---|---|---|
| [ ] | [rytm / palett / övergångar / kamera] | [innehåll, logotyper, musik, karaktärer] |

## Verktyg och nycklar
Renderare: [HyperFrames / Remotion / HTML+Playwright / Canvas]. Röst: [Kokoro lokalt / ElevenLabs (betalt)].
Musik: [egen bädd / ACE-Step lokalt / licensierat spår]. Bild/video-modeller: [inga / Higgsfield (betalt)].
Nycklar läses från miljövariabler – klistra aldrig in hemligheter i briefen eller koden.
Kostnadstak: [0 kr / X kr] – fråga innan något kostar.

## Karaktärsbibel (om figurer finns)
| Figur | Utseende (silhuett, färger, proportioner) | Personlighet / hur den rör sig | Får aldrig |
|---|---|---|---|
| [ ] | [ ] | [ ] | [ ] |
Referensark: [fil, se prompts.downloaded.character-sheet]

## Beat sheet (tidslinje)
| # | Tid | Vad händer (en tydlig handling) | Känsla | Övergång ut | Ljud |
|---|---|---|---|---|---|
| 1 | 0:00–0:03 | Hook: [ ] | | | |
Regel: något händer i varje scen; varje övergång är motiverad (rörelse, form, ord eller ljud bär över).

## Text på skärmen (exakt)
| Tid | Text (ordagrant) | Källa/fakta-id |
|---|---|---|
Bara text i den här tabellen får synas. Siffror och påståenden kommer från faktabanken.

## Arbetsflöde och grindar (stanna och visa vid varje)
1. Storyboard: beat sheet + en skiss/stillbild per scen → godkännande.
2. Stilrutor: 3–4 färdiga stillbilder i slutlig stil → godkännande.
3. Svåraste 3 sekunderna: renderade i full kvalitet med ljud → godkännande.
4. Hela filmen som snabbutkast (540p) → kritikloop (09-critique-loop.md) tills alla betyg ≥ 8.
5. Master + omkomponerade format.

## Kritikloop
Efter varje utkast: kontaktark, strips kring snabba moment, mobiltest, loop-/determinismkontroll,
betyg 1–10 per kriterium, åtgärda de tre sämsta, rendera om.

## Leverabler
- MP4-master per format (9:16, 1:1, 16:9), SRT om text/röst finns
- Källkod + renderkommando, cues.json, beats.json
- Tillgångs- och licenslogg (varje bild, font, ljud: källa och licens)
- Kostnadslogg och lista över kända brister
```
