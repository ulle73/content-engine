# carousel-generator-kie — importanteckningar

**Källa:** `Downloads/hyperframes-remotion/Carousel-Generator-Kit/Carousel Generator Kit/` (kie.ai-versionen,
Soft Pastoral Editorial). Licens: ingen angiven — endast egen användning.

**Var:** runtime `library/kits/carousel-generator-kie/carousel/`, skill `.claude/skills/carousel-generator-kie/SKILL.md`
(bytt namn från `carousel`), utdata `work/carousel-generator-kie/`.

## Borttaget / ändrat
- `upload.py` (catbox.moe / 0x0.st) → avstängd stub. kie.ai-vägen kräver `KIE_API_KEY` i repo-rotens `.env`
  OCH `CAROUSEL_STYLE_REFERENCE_URL` (egen publik URL till stilreferensen).
- `capture.py` → vanlig Playwright (ingen UA-förfalskning).
- `@justjay.md` / `@build.withjade` / "MADE BY CLAUDE · 2026" / startbilden "This carousel was made by Claude"
  → parametrar, standard `@golfkuponger` / `Golfkuponger`.
- Voxelmaskotar 4 × ~6 MB PNG (23 MB) → WebP q92 med alfa (~0,7 MB totalt); stilreferens PNG → JPG.
  Maskotarna är AI-genererade av kitförfattaren (Higgsfield-jobb-id i metadata), orange kubfigurer — inte
  Anthropics officiella figur, men färgen påminner om Claude; använd med omdöme.
- Nytt gratisläge: `carousel_run.py build <run>` = render + export med egna foton som `bg_file`
  (eller ren pastellhimmel). Gratisvägen är standard; `generate`/`produce` är betalda.

## Windows-anpassningar
UTF-8 överallt, `carousel_config.py` (repo-rot, `WORK_DIR`, `resolve()`, `launch_browser()`), väntan på fonts,
MIME-fix så WebP-maskotar bäddas in rätt, venv `library/.venv`. Kitet hålls självständigt (äldre renderare
utan diagram); `template.html` är byte-identisk med carousel-generator/template-pastoral.html.

## Verifiering (2026-10-08, gratisvägen)
Pastoral (5 bilder med golffoton, alla 4 maskotar, hero/stats/bars/maskot-overlay) och 90s renderade och granskade.
kie.ai-bakgrunder **ej körda** (ingen nyckel, kostar pengar) → `unverified`.

## Kända problem
- Ibland laddas Inter för sent och varumärkesetiketten faller tillbaka på en annan font.
- Ingen diagrammodul (line/column/…) i detta kit — använd carousel-generator eller carousel-kit för diagram.
- Blocken dial/chips/image är inte renderade i detta kit (unverified).
