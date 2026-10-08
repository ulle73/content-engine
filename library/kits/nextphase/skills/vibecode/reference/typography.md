# Typography

Two families, four roles. Nothing else.

## The families

```css
--vc-display: 'Anton', 'Archivo Black', 'Oswald', Impact, sans-serif;
--vc-body:    'Inter', 'Figtree', -apple-system, sans-serif;
```

**Display** is a heavy condensed grotesque in all caps — measured off REF-B's
"FUTURE OF / VIDEO EDITING" at 27.5s. Flat terminals, tight counters, very
little sidebearing. Anton is the closest free match and is the default.

**Body** appears only in the eyebrow and the rare subline. If you find yourself
setting a paragraph, the beat needs a real screenshot instead.

**Vendor both fonts into every `seg-NN/`.** HyperFrames renders in a headless
browser with no network and no system font fallback worth having; a missing
Anton silently becomes Impact and every measured line length is wrong.

## The four roles

| Role | Class | Size | Notes |
|---|---|---|---|
| Poster line 2 | `.vc-display` | `--vc-display-xl` 13cqh | the hero line of a title beat |
| Poster line 1 | `.vc-display-sm` | `--vc-display-lg` 7.4cqh | the setup above it |
| Caption | `.vc-caption` | `--vc-caption` 4.2cqh | in the lozenge, lower centre |
| Label | `.vc-label` | `--vc-label` 1.95cqh | under a tile, on a chip |
| Eyebrow | `.vc-eyebrow` | `--vc-eyebrow` 1.55cqh | body font, 800, `.30em` tracking, yellow |

## The scale jump is the design

REF-B sets "FUTURE OF" at roughly half the size of "VIDEO EDITING". That
**ratio is the poster** — a title beat with two lines at the same size has no
hierarchy and reads as a slide. Keep line 2 at 1.7–1.8× line 1.

## The hard shadow

Display type carries the same offset shadow as paper: `--vc-shadow-x/y` in
`--vc-ink`, zero blur. It is what plants the type on the ground instead of
floating it. `.vc-display` applies it; do not add a second, softer one.

## ⚠ Size type in `cqh`, and put `.vc-frame` on the root

Every size here is in `cqh` so one scale serves the whole style. `cqh` resolves
against a **size container** — the composition root must carry `.vc-frame`
(which sets `container-type: size`). Without it, type renders at a fraction of
its intended size and the layout still looks plausible, so this is the first
thing to check when a scene looks subtly wrong.

A percentage `font-size` resolves against the *parent's* font-size, not the
frame. Never size type in `%`.

## Copy rules

- **Every string comes from this video.** The speaker's own words at their onset
  in `transcript-tight.json`, the real name of the thing on screen, or a
  verified figure. Kit copy in `components/` is placeholder;
  `scripts/check-vibecode.sh` fails the render if it survives.
- **All caps for display, caption and label.** The eyebrow too. Sentence case
  appears nowhere in either reference.
- **One idea per poster.** Two lines, six words, hard stop.
- **Never emojis.** Build a navy pictogram on a paper tile instead — REF-B does
  exactly this at 34s and it is stronger than REF-A's emoji.
