# Own-images layouts (skill 2) — the 5 reference designs

Skill 2 takes the user's OWN photos (a roofer's job sites, a dentist's clinic, a creator's
selfies) and turns each one into a finished slide. There is no stock or AI imagery, and no
style-sheet world: **the photo is the world**. The design lives entirely in the typography
laid over it.

References are in `library/kits/carousel-kit/carousel/assets/own-images/layout-refs/`. They are other creators' work.
Replicate the *treatment* (type system, layering, furniture), never their words, handles,
logos or series names.

Common to all five:
- Full-bleed photo, 4:5, no frames or panels (except #2's hairline rules).
- A light film grade + grain over the whole frame, so type and photo sit in one world.
- Type is 1–2 colours: white, or ONE accent pulled from the photo (yellow, orange, lime).
- A person or clear subject in the middle third; the type is placed *around* or *behind* it,
  never across the face.
- Small furniture (handle, save/swipe cue, series label) at the edges.

---

## L1 · Scattered serif (`01-scattered-serif.jpg`)
- **Headline:** a short sentence, lowercase, in a light didone/modern serif (white), **one
  word per line**, each word dropped at a different x position so the phrase zig-zags down
  around the subject ("there / won't / always / be / a / solution").
- **Label:** an outlined pill with thin white stroke, top-left ("lesson #20" → our series
  number).
- **Series lockup:** bottom-right, stacked serif with italic numerals ("24 lessons in 2024" →
  e.g. "30 tips in 30 days").
- **Photo needs:** subject centred; open space left and right of them for the words.
- **Build:** words absolutely placed from a per-slide list of (x, y) or auto-placed into the
  empty regions of the subject mask. No cutout layering (text sits over the photo).

## L2 · Editorial serif (`02-editorial-serif.jpg`)
- **Frame furniture:** handle top-left + small logo lockup top-right, a hairline rule under
  them; a hairline rule above the footer; footer URL left, "READ CAPTION" right. All small
  bold sans caps, white.
- **Headline:** 2 lines, big transitional serif in a warm **yellow pulled from the photo**,
  left-aligned, tight leading ("My / Intention").
- **Body:** a 4–6 line paragraph in the same yellow, uppercase regular sans, left-aligned,
  under the headline.
- **Doodle:** a hand-drawn white arrow looping from the text to the subject.
- **Photo needs:** subject on one side (right), calm wall/space on the other for the text.
- **Build:** the business's logo goes top-right (see `logos.md`). Headline colour picked from
  the photo's warm highlights, then checked for contrast against the area it sits on.

## L3 · Behind-subject + orbit text (`03-behind-subject-orbit.jpg`)
- **Headline:** huge bold grotesk (white), 1 line, **behind the subject's head**:
  photo → headline → Vision cutout (`cutout.py`). A small bold kicker above-left
  ("Photography") and a byline right-aligned under it ("By Maciejsphotos." → "By @handle").
- **Orbit text:** a repeating location/tagline string set on an SVG `textPath` that spirals
  around the subject's body ("Tokyo, Japan, Tokyo, Japan…" → "Austin, TX · Roof Repair ·").
- **Label:** a tiny bold label mid-right ("Japan Vol 2" → "Vol 1").
- **Photo needs:** one person/object with head in the upper-middle; cutout must be clean.
- **Build:** spiral path generated from the subject mask's bounding box; text at ~16px bold.

## L4 · Caps + script punch (`04-caps-plus-script.jpg`)
- **Headline:** 3 lines of heavy condensed-ish sans caps, white, centred, tight leading; ONE
  word in the accent (orange) caps ("HARDEST"); then a **huge italic serif** word in the accent
  that overlaps the caps above it ("posting…").
- **CTA:** "LET ME EXPLAIN." accent caps bottom-left + a hand-drawn accent arrow to the right.
- **Footer:** handle in small italic serif left · bookmark icon + "save for later" centre ·
  arrow right. White.
- **Photo needs:** subject in the lower half; top 40% calm (wall) for the headline.
- **Build:** accent sampled from a warm object in the photo (the orange cushion). Heavy grain.

## L5 · Cascading serif (`05-cascading-serif.jpg`)
- **Kicker:** small lowercase serif, top-centre, in the accent ("why i stopped reading
  self-help books").
- **Headline:** big lowercase serif, **mixed roman and italic**, in a lime/yellow accent,
  cascading diagonally down along the subject's motion; words overlap the subject; decorative
  quote marks and tiny spark strokes near the first word.
- **Aside:** a handwritten/mono parenthetical note in the accent, bottom-right
  ("(not just who i want to be…)").
- **Photo needs:** a subject in motion with a clear diagonal; urban/outdoor.
- **Build:** words placed along a diagonal line fitted to the subject mask's long axis.

---

## Choosing a layout for a photo
| Photo | Best layouts |
|---|---|
| Person centred, space both sides | L1, L3 |
| Person to one side, calm wall | L2 |
| Person low in frame, calm top | L4 |
| Person moving / diagonal composition | L5 |
| No person (a roof, a clinic room, a product) | L2, L4 (type in the empty area), L3 if the object cuts out cleanly |

Use one layout for the cover and vary within the set (same fonts + accent across all slides),
so a carousel reads as one piece.
