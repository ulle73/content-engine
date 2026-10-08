# Content Engine

## Skapa innehåll
För allt som ska skapas (video, reels, annonser, karuseller, animationer, bilder, copy): börja med
skillen **`/studio`** (`skills/studio/SKILL.md`). Den söker i Content Library (`library/`) efter
färdiga, snygga mallar och effekter och utgår från dem. Stilen är fri – brand-skillen är ett
utgångsläge. Fakta i reklam kommer från faktabanken (`skills/golfkuponger-friskvard`).
Arbetsfiler och renderingar läggs i `work/` (gitignorerat).

## Kod
- Tester: `.venv/Scripts/python.exe manage.py test engine --settings=engine.test_settings`
- `main` deployas till produktion (Render) – jobba på en branch och öppna PR.
- Efter ändringar i `library/`: `python library/tools/build_catalog.py`.
