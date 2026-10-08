# 09 — Logos (the real mark of whatever the carousel is about)

**If the carousel talks about a specific company, product or platform, its real logo goes on
the slides.** Instagram, Ferrari, Anthropic, a client — use the actual mark, never a lookalike,
never an AI-invented one.

## 1. Get the logo (every run, before writing the plan)
```
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py --list "<Company>"                    # see candidates
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py work/carousel-kit/logos "<Company>"      # best match
library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/fetch_logo.py work/carousel-kit/logos "<Company>" --pick 2 --as <company>-glyph
```
- Pulls a **vector SVG** from Wikimedia Commons and renders a **transparent PNG** next to it
  (longest side 1024px, own aspect ratio). Source page + licence go in `assets/logos/logos.json`.
- **Open the PNG and check it** — right company, *current* version (not a 2016 mark), not a
  combined/sub-brand file. Fetch both the icon/glyph and the wordmark when they differ.
- Nothing usable on Commons → use the company's official press / brand-kit page, save it into
  `assets/logos/`, and add its source to `logos.json` by hand.
- Several companies in one carousel → fetch each one's logo.
- Check `assets/logos/` first — reuse a logo already fetched.

## 2. Local $0 path (HTML templates)
Place the logo file directly in the slide — it is a real asset, sharp at any size.
- **Where:** a logo lockup on the hook slide (near the topic chip / kicker, or with the hero
  number), and wherever the slide is *about* that company (e.g. next to its bar in a chart,
  on a comparison card). Small and deliberate — a label, not a watermark on every slide.
- **Colour vs. the style sheet:** style sheets restrict the palette. Default to a **single-colour
  version in the style's type colour** (bone white on Archival, moon white on Midnight — done
  with a CSS `filter: brightness(0) invert(1)` or a mono SVG). Use the **full-colour** mark only
  inside a contained element (a card, a "source" chip, a screenshot frame), where it reads as
  evidence, not as decoration.
- **Never** recolour it into non-brand colours, stretch it, crop it, add effects, or redraw it.
  Keep clear space around it (≈ the height of its smallest element).
- The logo does not replace the headline or the proof — the middle of the slide still carries
  the chart / stat / screenshot.

## 3. Paid path (Higgsfield / kie.ai image generation)
Image models invent logos badly. So **always hand the real logo to the model**:
1. **Upload the PNG as a reference image** alongside the style sheet
   (Higgsfield: `media_upload` → `curl PUT` → `media_confirm`, then pass the media id in
   `medias` with role `image_references`; kie.ai: add it as a second input image).
2. **Describe it in the prompt**, explicitly naming which reference is which:
   *"Reference image 1 is the STYLE SHEET — copy its style only. Reference image 2 is the
   OFFICIAL INSTAGRAM LOGO — a rounded-square camera glyph with a purple→pink→orange→yellow
   gradient and a white outline camera. Reproduce it exactly as given, small, in the top-left
   of the ink panel. Do not redraw, restyle or recolour it."*
3. Say **where** it goes and **how big** (e.g. "about 8% of the slide width").
4. **Check every output** for a distorted logo. If the model mangles it, the fix is the hybrid
   route: generate the image *without* the logo and composite the real file on top in HTML.

## Attribution
Logos are trademarks of their owners, used here to identify the subject (editorial use).
Don't imply endorsement or partnership, and don't use a logo as your own brand mark.
