# Content Engine

## Skapa innehåll
För allt som ska skapas (video, reels, annonser, karuseller, animationer, bilder, copy): börja med
skillen **`/studio`** (`skills/studio/SKILL.md`). Den söker i Content Library (`library/`) efter
färdiga, snygga mallar och effekter och utgår från dem. Stilen är fri – brand-skillen är ett
utgångsläge. Fakta i reklam kommer från faktabanken (`skills/golfkuponger-friskvard`).
Arbetsfiler och renderingar läggs i `work/` (gitignorerat).

## Ändra en befintlig film
Alla filmer ligger som självständiga projekt i `work/<mapp>/` – översikt i `work/FILMER.md`. Följ skillen
**`/film`** (`skills/film/SKILL.md`): ändra i filmens `film.json`, bygg bara det som behövs (`./make.sh del|ljud|bild`),
läs `out/QA.md` och titta på `out/qa-kontakt.png` innan leverans.

## Kod
- Tester: `.venv/Scripts/python.exe manage.py test engine --settings=engine.test_settings`
- `main` deployas till produktion (Render) – jobba på en branch och öppna PR.
- Efter ändringar i `library/`: `python library/tools/build_catalog.py`.
