---
name: ny-video
description: Det fasta flödet när en ny video ska göras från en beställning ("jag vill göra en instruktionsvideo…", "gör en reel om…") – fasta frågor, väg A (referensfilm från kända företag → rea-video) eller väg B (tre riktningar ur idébanken i olika genrer), Blender-frågan och materiallistan, anti-slop-kontroll, storyboard, bygg och lärande tillbaka till banken. Använd ALLTID först när en ny video eller reel ska skapas; för ändringar i en befintlig film gäller /film.
---

Läs och följ `skills/ny-video/SKILL.md` i repots rot – den fullständiga instruktionen.

Snabbstart:

```bash
python scripts/riktningar.py work/<film> --forslag "<beställningen>"   # väg B: 3 idéer i olika genrer
python scripts/riktningar.py work/<film>                              # → out/riktningar.png
python library/tools/find.py "<ord>" --type idea                      # idébanken
./make.sh storyboard                                                  # → out/storyboard.png, godkänns före bygget
```
