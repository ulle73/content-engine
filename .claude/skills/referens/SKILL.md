---
name: referens
description: Från en känd, etablerad företagsfilm till vår egen version – hitta 5–8 förslag, Jonas väljer, hämta, bryt ner klipp för klipp med rea-video (berättelse, tempo, hur varje klipp är gjort, text och ljud), gör referensens berättelse till ett storyboard-ark och skriv om det till vårt innehåll. Använd ALLTID när Jonas ber om kända/etablerade företagsvideor, inspiration eller referenser, skickar en videolänk han gillar, eller säger "gör en sån här".
---

Läs och följ `skills/referens/SKILL.md` i repots rot – den fullständiga instruktionen.

Snabbstart:

```bash
.venv/Scripts/python.exe -I library/techniques/hamta.py "<länk>"                       # → work/references/<slug>/video.mp4
cd work/references/<slug>; export PYTHONIOENCODING=utf-8; R=../../_verktyg/rea-video/.venv/Scripts/rea-video.exe
$R decompose video.mp4 -o rea --lang en && $R review rea   # fyll rea/review_answers.json, sedan:
$R apply-review rea --by Claude && cd ../../..
.venv/Scripts/python.exe scripts/storyboard.py work/references/<slug> --fran-rea work/references/<slug>/rea
```
