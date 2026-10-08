# carousel-generator — importanteckningar

**Källa:** `Downloads/hyperframes-remotion/Carousel-Generator-Kit 0$/Carousel Generator Kit/` (gratisversionen).
Licens: ingen angiven — endast egen användning.

**Var:** runtime `library/kits/carousel-generator/carousel/`, exempel `library/kits/carousel-generator/examples/`,
skill `.claude/skills/carousel-generator/SKILL.md` (bytt namn från `carousel`), utdata `work/carousel-generator/`.

## Borttaget / ändrat
- `upload.py` (catbox.moe / 0x0.st) → avstängd stub; betald väg kräver `CAROUSEL_STYLE_REFERENCE_URL`.
- `capture.py` → vanlig Playwright (ingen UA-förfalskning/dold automationsflagga, avvisar bara cookies).
- Hårdkodat `@justjay.md` / "made with claude" / "Built for the thinkers" i startplanen → parametrar,
  standard `@golfkuponger` / `Golfkuponger` / `golfkuponger.se` (`init "<ämne>" --handle --brand --tagline`).
- **Buggfix:** SKILL.md pekade på `assets/style-reference-archival.png` (och `-celestial.png`,
  `carousel-style-reference.png`) — rätt filer är `assets/styles/archival.jpg`, `celestial.jpg`, `midnight.jpg`.
- Installationsprompter (READ-ME-FIRST, START-HERE med `~/Library/Caches`) togs inte med.

## Windows-anpassningar
Samma som carousel-kit: UTF-8 överallt, `carousel_config.py` med repo-rot / `WORK_DIR` / `resolve()` /
`launch_browser()`, väntan på `document.fonts.ready`, MIME-fix för webp, `bg_seed: null`-fix, venv `library/.venv`.
Skripten är nästan identiska med carousel-kit men kitet hålls självständigt (äldre mallversioner).

## Verifiering (2026-10-08, gratisvägen)
Golfkuponger-demo renderad och granskad: 5 stilar (midnight, archival, celestial, pastoral, 90s), 4 diagram,
6 block, 7 bakgrundsscener. Planer i `work/carousel-generator/runs/demo-*`.

## Kända problem
- `examples/` är kitförfattarens renderingar med hans handtag (@justjay.md), "made with claude" och CC-foton
  (Ferrari m.m.) — endast referens, publicera inte vidare.
- 90s-bildtexten har låg kontrast på ljusa foton. kie.ai-vägen ej körd (`unverified`).
