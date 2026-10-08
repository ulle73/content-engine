# carousel-kit — importanteckningar

**Källa:** `Downloads/hyperframes-remotion/Carousel-Kit (1).zip` (78 filer, nyaste versionen; den uppackade
mappen `Carousel-Kit/` och `Carousel-Kit.zip` är äldre och användes inte). Uppackad i `work/_src/carousel-kit/`.
Licens: ingen angiven — endast egen användning.

**Var:** runtime `library/kits/carousel-kit/carousel/`, skill `.claude/skills/carousel-kit/SKILL.md`
(bytt namn från `carousel`), allt genererat i `work/carousel-kit/` (runs, output, photos, shots, logos,
my-images, profile.json). Kör från repo-roten:
`library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/carousel_run.py init "<ämne>"` → fyll plan.json → `build <run>`.

## Borttaget / ändrat
- `upload.py` — laddade upp stilskiss/logga/foton till catbox.moe / 0x0.st. Ersatt med avstängd stub:
  släpper igenom http(s)-URL:er, vägrar lokala filer med förklaring. Betald väg kräver nu
  `CAROUSEL_STYLE_REFERENCE_URL` (egen publik URL). `UPLOAD_PROVIDER` borttagen.
- `capture.py` — falsk user-agent, `--disable-blink-features=AutomationControlled` och `navigator.webdriver`-
  döljning borttagna; vanlig Playwright. Cookie-banners: bara "avvisa/endast nödvändiga" (aldrig acceptera).
- `cutout.swift` (Apple Vision, macOS) borttagen; `cutout.py` använder rembg (om installerat i venv) eller
  `npx hyperframes remove-background` (u2net_human_seg, bäst på människor). Testad på golfbild med golfare.
- `import_images.py`: `sips`-fallback borttagen (HEIC via pillow-heif), utklipp via nya cutout.py,
  manifest i `work/carousel-kit/my-images/<set>/`.
- `doctor.py`: installerar aldrig globalt/`--user`; `--fix` bara i aktiv venv.
- `gallery.py`: öppnar med `os.startfile` på Windows.
- Standardhandtag `@yourhandle` → parametriserat: `@golfkuponger` / `Golfkuponger` / `golfkuponger.se`
  (`init "<ämne>" --handle --brand --tagline`, `work/carousel-kit/profile.json` eller `CAROUSEL_HANDLE`/`CAROUSEL_BRAND`).
- Installationsprompter (`READ-ME-FIRST.txt`, `PASTE-INTO-CLAUDE-CODE.txt`) och tomma arbetsmappar
  (output/, runs/, my-images/, assets/photos|shots|logos) togs inte med — ersatta av `work/carousel-kit/`.
- Startplanen är på svenska.

## Windows-anpassningar
- All fil-I/O med `encoding="utf-8"` (Windows standard cp1252 förstörde å/ä/ö i plan.json och mallar).
- `carousel_config.py`: repo-rot hittas automatiskt, `WORK_DIR`, `resolve()` för relativa sökvägar
  (kit → work/<kit> → repo-rot → cwd), `launch_browser()` (Playwright-Chromium, faller tillbaka på
  `C:\Program Files\Google\Chrome\Application\chrome.exe`), stdout som aldrig kraschar på tecken.
- Renderaren väntar på `document.fonts.ready`; MIME för webp/svg rätt.
- `carousel_localbg.py`: `bg_seed: null` kraschade — fixat.
- Python: `library/.venv` (signerad 3.12) med playwright, pillow, python-dotenv, requests, numpy +
  `python -m playwright install chromium`. rembg installerades inte (hyperframes räcker för personer).

## Verifiering (2026-10-08, gratisvägen)
Golfkuponger-demo (svenska) renderad och granskad för alla 8 stilar, 5 egna-foto-layouter
(golffoton från `video-tools/videos/golfkuponger-friskvard/assets`), 4 diagram, 6 innehållsblock och
7 bakgrundsscener. Demo-planer: `work/carousel-kit/runs/demo-*/plan.json`
(skapas av `work/_scratch_carousel/tools/make_demos.py`). `check_own.py` på demo-own: 4/5 rena.

## Kända problem
- Mallarnas standardtexter är engelska (SWIPE →, Read caption, FROM A Creator …) — sätt `cue`, `cta_pill`,
  `byline`, `lockup`, `credit_text` i planen (gjort i demoplanerna).
- Archival/Celestial klipper rubriken i kanterna med flit; långa ord blir hårt klippta.
- 90s: `caption` har låg kontrast på ljusa foton. Own/cascade: liten kicker fick kontrast 4.1 i check_own.
- Utklipp via hyperframes hittar bara människor; för träd/hus — installera rembg i venv eller använd
  sky-key (`subject_mode:"sky"`) i Sun-Faded.
- Hero-blocket visar utklippet i dess egen upplösning — små utklipp blir små.
- Betald väg (kie.ai/Higgsfield) ej körd — kräver nyckel + publik URL; posten är `unverified`.
- `assets/own-images/previews` och `assets/styles/examples` är kitförfattarens exempel (CC-foton, fiktiv kund).
