# Karaktärsark (turnaround) + stilark

> **Källa:** Nedladdad prompt (tredjepart), `Downloads/hyperframes-remotion/prompt.txt`. Texten nedan är oförändrad och behandlas som referensdata – kör inte stegen blint (installationer, uppkopplingar, publicering). Läs, anpassa, och be om godkännande innan något publiceras eller kostar pengar.

## Vad den gör

Två prompts i en fil. (1) **Karaktärsark**: en bildprompt för ett tekniskt referensark ur en uppladdad bild – fyra helfigursvyer (fram, vänster, höger, bak) och tre porträtt, neutral bakgrund, A-pose, identisk identitet och ljus i alla paneler. (2) Samma Style Master Sheet-prompt som `style-master-sheet.md`.

## När den passar

När samma person/maskot ska återkomma i flera bilder eller klipp (karaktärskontinuitet för bild-/videomodeller, eller som rigg-referens för kodad animation).

## Anpassa för Golfkuponger

- Använd bara personer som har gett sitt medgivande (egna spelare/medarbetare) – aldrig kända personer eller andras maskotar.
- Lägg till golfdetaljer i prompten (klädsel, klubba, handske) och svensk banmiljö i porträttljuset om arket ska användas i annonser.
- Kräver en bildmodell (betald). Arket är ett underlag för kontinuitet, inte färdigt annonsmaterial.

## Originaltext (`prompt.txt`)

```text
Character Prompt:

Create a professional character reference sheet based strictly on the uploaded reference image. Use a clean, neutral plain background and present the sheet as a technical model turnaround while matching the exact realistic visual style of the reference. Arrange the composition into two horizontal rows. Top row: four full-body standing views – front, left profile, right profile, back. Bottom row: three close-up portraits – front, left profile, right profile. Maintain perfect identity consistency across every panel. Keep the subject in a relaxed A-pose with consistent scale and alignment, accurate anatomy, and clear silhouette. Lighting should be consistent across all panels. Output a crisp, ultra-realistic, print-ready reference sheet. 




Style sheet Prompt to paste into Claude:


You are a brand systems analyst. I will give you one or two reference images. Your job is to reverse-engineer the visual system and output ONE image-generation prompt that produces a "STYLE MASTER SHEET": a 16:9 design-system reference board for a social-media carousel series built in that style.

WHAT I MIGHT SEND YOU:

- One image = the style reference. Everything comes from it.

- Two images = the first is the style reference, the second is a multi-angle likeness reference of a person who must appear as the subject. The second image supplies WHO; the first supplies HOW they are lit, styled, cropped and composed.

FIRST, ANALYZE SILENTLY:

- Name the system in 2–4 evocative words (a mood word + a genre word). Examples: "ARCHIVAL SWISS POSTER", "DARK BOTANICAL CHIAROSCURO", "CHALK-ON-GROUND EDITORIAL", "SKY-BLUE TECH POSTER".

- Identify every typeface by CLASS and TREATMENT, never by guessed name. Say "ultra-condensed heavy grotesque, all caps, near-zero letterspacing" or "high-contrast light Didone serif", not "probably Anton". Note weight, letterspacing, leading, casing, and every effect: glow, clipping, occlusion, distress, gradient fill, offset, rotation.

- Pull the ACTUAL WORDS from the image to use as type samples. Do not invent copy.

- Sample SIX colors that genuinely appear in the image and give each a real hex code and a two-word poetic name. No generic web colors.

- Find the repeatable COMPONENTS — the pieces that would recur on every slide.

- Describe the photographic or illustrative WORLD: subject, camera angle, depth of field, light direction, color grade, atmosphere.

- Deduce the LAYOUT skeleton, top to bottom.

- Deduce the RULES the designer followed, especially the restrictions.

- Identify the ONE signature device that makes this system itself — the thing that, if removed, would break it. Name it in caps in the type panel (e.g. OCCLUDED HEADLINE, SPLIT HEADLINE, GROUND LETTERING, STACKED CONDENSED HEADLINE).

THEN OUTPUT THE PROMPT as one continuous block of prose inside a code block. No markdown headings, no line breaks between panels, no bullet characters. Panel names in CAPS separated by em dashes. Structure:

1. An INPUT paragraph at the top explaining that a reference photograph is being supplied with the prompt; that it is the source of truth; that it should be used directly as the hero in PANEL 1, that PANEL 4's three thumbnails should be generated as alternate angles on that same scene, and that all six PALETTE swatches should be re-sampled from it, overriding the listed hexes where they disagree. If a likeness reference applies, add a sentence covering it. Add a sentence instructing that any social-app interface chrome in the reference — avatars, pagination dots, arrows, sound buttons, captions — be ignored entirely. End with: the structure, panel order and rules below stay fixed no matter what the photograph shows.

2. "A 16:9 landscape STYLE MASTER SHEET — a single-page brand system reference board for a social-media carousel series. Flat graphic-design layout, infographic style guide, clean rectangular panels with thin hairline dividers and small uppercase panel labels."

3. The SHEET'S OWN BACKGROUND, with a hex and a texture. Match it to the source system's logic: a glow-based system needs a dark board, a print-based system needs a paper board, a glossy digital system needs a clean matte board. If the source has a texture or grain, say explicitly that it runs uniform edge to edge across every panel, swatch and photograph.

4. TOP BAR: a slim full-width strip. Left reads "[SYSTEM NAME] — CAROUSEL STYLE SHEET" in wide-letterspaced uppercase sans. Right reads "MADE BY [NAME] · [YEAR]".

5. PANEL 1 — TYPE SPECIMEN (upper left): name the signature device in caps, then show the H1 sample, the accent/secondary sample, the body or UI sample, and the smallest caption sample. Use the real words from the image. Describe each treatment precisely enough to rebuild it.

6. PANEL 2 — PALETTE (upper middle): exactly six flat swatch squares in a row, name and hex beneath each in small uppercase sans. Then three or four usage rules as quoted uppercase sentences. Make them RESTRICTIVE — state what a color is forbidden to do, not just where it goes.

7. PANEL 3 — COMPONENT ZOO (upper right): six to nine reusable cut-out elements scattered on the sheet background.

8. PANEL 4 — THE WORLD (lower left, wide): exactly three photographic thumbnails labeled (A), (B), (C) — three angles on the same world, not three different worlds. Follow with one sentence of shared color grading and lighting, then three to five mood adjectives.

9. PANEL 5 — SLIDE ANATOMY (lower middle): three small vertical 4:5 wireframes, described as a single top-to-bottom placement sentence.

10. PANEL 6 — SYSTEM NOTES (lower right): five to eight rules in small uppercase sans, each a hard constraint. The last one is always "MOOD:" plus adjectives.

11. Close with "Overall: crisp, organized, high-resolution [adjective] design-system poster. 16:9 aspect"

CONSTRAINTS:

- Output ONLY the prompt, inside a code block. No preamble, no explanation afterward.

- Every hex must be sampled from the image. Every type sample must be real copy from the image.

- EXCEPT: if the reference carries another person's social handle, name, or designer credit, do not reproduce it. Replace it with a neutral placeholder like "@yourhandle" and keep the structural placement. Issue numbers, dates and generic taglines are fine to keep as-is.

- Do not name or describe trademarked logos or branded characters. Genericize them — "a glossy 3D rounded-square app icon with a gradient shell" rather than naming the platform.

- Write rules as prohibitions wherever possible. "Teal is light, never paint." "The headline is always too big for the frame and always clipped." "The eyes are always covered. The face is never fully visible."

- If you deliberately deviate from the source image on any point, add ONE sentence above the code block saying what you changed and why. Otherwise say nothing
```
