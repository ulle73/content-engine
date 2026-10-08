# Glass & brand — the Midnight Bioluminescent system

Everything the template draws is **glass**. There is no opaque surface in this style.

## Palette (the only colours that exist)
| token | hex | rule |
|---|---|---|
| Void black | `#08080A` | the field. At least 40% of every slide stays unbroken black. |
| Ash charcoal | `#1A1B1E` | the tint inside glass panels |
| Moon white | `#FFFFFF` | primary type |
| Bioluminescent teal | `#3FBFB2` | **light, never paint** — glow only |
| Ember amber | `#E9A33C` | tiny warm accents in the scene's foreground flora **only** |
| Fog gray | `#7C7C82` | secondary type: labels, notes, footer, microcopy |

**All type is moon white or fog gray. No other text colour exists** — teal never colours text.

## The glass material (CSS vars in `template.html`)
A panel on a black scene needs more than a blur, so every surface is built from four parts:
1. `--glass-tint` — a frosted body, `rgba(26,29,32,.52)`, so the panel reads as an object
2. `--glass-fill` — a diagonal white gradient sheen (16% → 3%)
3. `--glass-edge` — a 1px light edge, `rgba(255,255,255,.28)`
4. `--glass-shadow` — deep drop shadow + inner top highlight + a faint teal spill along the bottom

Plus a `::after` specular sweep across every panel. Change these five vars and the whole set
re-skins at once. Surfaces that use it: data cards, screenshot frames, chips, caption pills,
hero captions, the topic chip.

## Type
- **Headline** — Cormorant Garamond Light 94px, centred, moon white, soft white bloom.
- **Accent word** — ONE per slide, in the **glass capsule**: serif inside a bright ring with
  light pooling under its bottom edge. Never more than one capsule per slide.
- **Everything else** — Inter. Labels and the topic chip are uppercase with wide tracking.
- Serif against sans is the whole typographic idea. Don't set body copy in the serif.

## Anatomy of a slide (top → bottom)
1. **Rail** — glass topic chip (left) + `index / total` counter (right)
2. **Headline** + the one **glass capsule** accent word
3. Optional **caption pill** (glass)
4. **Content** — the proof: glass data card, glass screenshot frame, chips, or a hero cutout
5. **Action block** (sits just above the footer) — the bright frosted button + fog-gray microcopy
6. **Footer** — hairline rule, then `@handle · tagline · brand label`

## Plan fields this style adds
`cta_pill` (button text) · `cta_soft` (the trailing gray word, e.g. "now") · `microcopy`
(one small line under the button) · `tagline` (footer middle; can be set once on the plan) ·
`kicker` (small uppercase line above the headline) · `bg_scene` / `bg_seed` / `bg_tweak`.

## Rules
- One glass capsule per slide. Two capsules kills the effect.
- Teal only glows: bar fills, the capsule ring, the active dial segment, stat-number bloom.
- Never put amber in the UI — it belongs to the flora in the scene.
- Keep the middle carrying proof, and keep the top black.
- The bright frosted button is the ONE light-on-dark element. Use it on the CTA slide, sparingly
  elsewhere.
