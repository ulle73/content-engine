# Blink – stor fråga och siffra som växlar grönt/guld (dashboardmall)

Enkel premiumgrafik som blinkar, som Caia och Libresse. Jonas valde designen 2026-11-26 efter tre rundor:

- **"Friskvårdsbidrag kvar?" är huvudfrågan**: lika bred som rubriken, två rader som standard (sista ordet på egen rad).
- **Stor siffra eller ord** (t.ex. 7 eller Sista dagen), **rubrik** under och **en vanlig textrad** sist – ingen knapp.
- **Läge a:** metallguld (brons → champagne → guld, mjukare kontrast sedan runda 3) med mörk guldkant och skugga på smaragd.
  **Läge b:** grön text med dämpad smaragdgradient (samma uppbyggnad som guldet) på dämpat antikguld. Inga linjer, ramar eller ornament.
- **Blink:** 0,4 s per läge (reglage, lägst 0,25 s = högst 2 blink per sekund av hänsyn till ljuskänslighet).
- **Texten fyller bilden** (46 px i sidorna, 96 px upptill/nedtill i 9:16). Jonas beslutade att de säkra zonerna inte
  gäller här; sidan märks `data-zon-fri` så att mallkontrollen hoppar över zonerna men fortfarande kontrollerar centreringen.
- Varje stor rad får en egen FontFace med uppmätt höjd (canvas), så att textrutan är lika stor som bokstäverna.
- **Loop, ingen slutbild** (Jonas runda 3): filmen är ett jämnt antal lägen långt så att den loopar sömlöst; Spotlight
  bara med `--satt slutbild=true`.
- **Utdata:** loopande mp4 (till Meta; reels och stories loopar den själva) och stillbild (läge a), i 9:16 och 4:5.
  Ingen gif: med 256 färger blir den mjuka bakgrunden prickig och randig (Jonas underkände den 2026-11-26).

```text
node library/templates/golfkuponger-blink/render.mjs --lokal [--format 9x16,4x5] [--satt stor=6] \
  [--satt "stor=Sista dagen"] [--satt "rad2=Dag kvar av året"] [--satt fraga_rader=en] [--ut work/x]
```
