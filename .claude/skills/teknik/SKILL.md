---
name: teknik
description: Teknikbanken – bevisade tekniker och metoder för video och karuseller (krokar, retention, vändningar, bevis, CTA, struktur). Använd ALLTID inför varje ny video eller karusell för att välja tekniker, och när någon skickar en länk till en video med en teknik/metod som ska sparas i biblioteket.
---

Läs och följ `skills/teknik/SKILL.md` i repots rot – den fullständiga instruktionen.

Snabbstart:

```bash
python library/tools/find.py "<idé> krok" --type technique          # inför varje video/karusell
.venv/Scripts/python.exe -I library/techniques/hamta.py "<länk>"                      # ny teknik från en länk
python library/techniques/make_library.py && python library/tools/build_catalog.py
```
