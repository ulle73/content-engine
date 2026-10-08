# Kritikloop – titta, betygsätt, fixa de tre sämsta

**Vad:** en fast granskningsrunda efter varje utkast. Modellen måste titta på riktiga renderade
bilder (inte på koden), betygsätta på sju kriterier och åtgärda de tre sämsta tills alla är ≥ 8.
Verktyg: `review.py` (ffmpeg + Pillow, kör med `library\.venv\Scripts\python.exe`).
**När:** efter varje utkast av allt som renderas – annonser, reels, karuseller i rörelse, långfilm.

## Kontroller

```bash
R=library/prompts/motion-studio-playbook/review.py
python $R sheet  out/draft.mp4 --every 1 --cols 5 --out work/prompts/x/sheet.jpg       # helheten
python $R strip  out/draft.mp4 --at 4.2 --span 0.4 --out work/prompts/x/strip.jpg      # snabba moment, ruta för ruta
python $R phone  out/draft.mp4 --at 0.8,5,12 --width 390 --out work/prompts/x/phone.jpg # läsbarhet i mobilstorlek
python $R loop   out/draft.mp4                                                         # loopsöm (position + fart)
python $R same   out/draft.mp4 out/draft-rerender.mp4                                  # determinism: identiska rutor?
```

## Prompt

```text
CRITIQUE LOOP – run after every draft, before you tell me anything is done.
1. Make the contact sheet (every 1 s), strips around every fast move or transition, the phone
   test (390 px wide) for every text moment, the loop check if it loops, and the determinism
   check (render twice, or render frames out of order, and compare).
2. Open the images and LOOK. Then score 1–10, one line of evidence each (cite timestamps):
   - Hook: is the point clear and moving within the first 1–1.5 s?
   - Readability at phone size: every word readable at 390 px, held long enough, inside safe zones?
   - Motion: easing, overshoot, stagger, no dead time, no jitter, nothing pops in/out?
   - Variety: do shots differ in scale, direction and rhythm, or is it the same move repeated?
   - Composition: hierarchy, alignment, breathing room, nothing cramped or clipped by accident?
   - Brand: colours, type, tone and facts as in the brief (only verified claims on screen)?
   - Sound sync: visual peaks and sound peaks coincide, cuts on beats, works muted too?
3. Pick the THREE lowest scores. For each: what exactly is wrong (timestamp), the fix, then apply it.
4. Re-render (draft quality), redo step 1–2. Repeat until every score is >= 8 or after 4 rounds;
   then show me the scores table, the sheet and what is still below 8 and why.
```

## Betygstabell

| Kriterium | Runda 1 | Runda 2 | Runda 3 | Bevis (tidpunkt) |
|---|---|---|---|---|
| Hook | | | | |
| Läsbarhet i mobil | | | | |
| Rörelse | | | | |
| Variation | | | | |
| Komposition | | | | |
| Varumärke | | | | |
| Ljudsynk | | | | |
