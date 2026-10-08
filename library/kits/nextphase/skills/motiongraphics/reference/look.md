# The look

The visual language. Everything here is enforced by `assets/tokens.css` — this file
explains *why*, so you can invent new scenes that still read as the same edit.

---

## 1 · The ground is never flat

A motiongraphics scene always has a **light source**. Flat `#000` with objects on it is
the amateur read and the fastest way to lose the style. Four grounds, all in tokens:

| Class | Light | Use for |
|---|---|---|
| `.mg-bg-bloom` | centre radial + a magenta wash from the bottom-left | the default — slam cards, object stages, caption takeovers |
| `.mg-bg-field` | violet glow rising off the **bottom edge**, indigo body, slow rotating cog silhouettes | the system-diagram backdrop (⌁ REF-A) |
| `.mg-bg-ribbon` | one big soft violet S-curve sweeping the frame | device mockups, persona circles (⌁ REF-A) |
| `.mg-bg-rails` | two soft violet streaks hugging the left and right edges | the screen stage — it lights the card without competing with it |

Every scene also gets `.mg-vignette`. It keeps the eye centre-frame and stops the
corners from banding on YouTube's encoder.

**The ground moves too.** The cogs rotate (~40s per revolution, `rotation` only). The
ribbon drifts. The bloom breathes ±3% scale. Slowly enough that you notice only if you
look for it.

---

## 2 · Four materials, and nothing else

Every object in both references is one of these. If you are about to invent a fifth,
you probably want one of these four restyled.

### Glass tile — `.mg-tile`
⌁ REF-B 0:41–0:45. Saturated violet-magenta fill, **2px white rim brightest along the
bottom edge** because it is lit from below, big radius, a bloom halo and a soft dark
shadow. A flat purple pictogram above a **light-weight** white label. Use for: a set of
peer concepts, steps, costs, roles — anything that comes in threes.

### Node pill — `.mg-pill`
⌁ REF-A 0:44–0:52. Near-black fill barely lifted off the ground, **2px lavender
stroke**, glow inside *and* out, white medium grotesque label with generous tracking.
Use for: any flow, sequence or dependency. Joined by ~2px lavender bezier connectors
with a glow, entering pill edge to pill edge in a smooth S-curve.

### Panel — `.mg-panel`
⌁ REF-A 0:30–0:58. The container a diagram lives in: `--mg-violet` 2px outline, big
radius, title centred on the top edge. Panels **stack vertically** and the whole stack
re-fits when one is added.

### Media card — `.mg-media`
The only way real media is ever shown. 3px near-white border, rim glow, deep shadow,
`.phone` variant for portrait. **Never full-bleed, never letterboxed.** A vertical
screenshot goes inside a phone card; a wide one inside a browser card. The border is
what makes it read as an *object on a stage* rather than a still someone pasted in.

---

## 3 · Colour

**One accent per frame.** Violet *or* magenta, never both fighting. Coral is reserved
for brand marks — a doc icon, a wordmark, an asterisk. Coral is never a background and
never a bar.

- **Violet** (`--mg-violet` `#843CF0`) — the workhorse. Diagrams, panels, rules, section
  titles, connectors, rings.
- **Magenta** (`--mg-magenta-hi` `#C054E4`) — the hot accent. The highlight box behind a
  slam word, the payoff moment, the one thing that must pop hardest in a chapter. If
  everything is magenta, nothing is.
- **Coral** (`--mg-coral` `#D87854`) — brand marks only.
- **White** — all body text, all labels. Never a coloured body copy.

The violet→magenta ramp is one continuous ramp; REF-A sits at the violet end and REF-B
at the magenta end. Pick a temperature **per video** in `PLAN.md` and hold it, rather
than drifting between them chapter to chapter.

---

## 4 · Type

Two faces do all the work.

**Heavy italic caps — `.mg-slam`, `--mg-font-slam` 900 italic.** Anything that slams:
the hero headline, the payoff, the CTA. Tight tracking (`-.02em`), white, with a soft
white glow and a deep shadow so it survives over any background. ⌁ Measured at ~100px
on a 1920 frame — big, but it is only ever one line.

**Clean grotesque — `--mg-font-ui`.** Everything that gets read: pill labels, panel
titles, bullets, card labels, captions. Weight carries the hierarchy — 700 for a point
headline, 500 for a body line, **300 for a glass-tile label** (⌁ REF-B's tile labels are
noticeably light, which is what stops the tiles looking like buttons).

**Serif — `--mg-font-display`.** Wordmarks and brand lockups only (⌁ REF-A's "Claude").
Never body copy, never a section title.

**Mono — `--mg-font-mono`.** Kickers and stat sub-labels, uppercase, `.18em` tracking.

Nothing below 22px survives YouTube's compression at 1080p. The scale in tokens is
measured off the references; don't invent sizes between the steps.

---

## 5 · Glow is the style

Rule 3 of the skill, restated because it is the thing people get wrong: **nothing has a
hard edge without a halo.** Every lit edge is 2px (`--mg-stroke`) and carries a
`--mg-glow-*`. The glow tokens are two-layer — a tight bright ring and a wide soft
bloom — because a single-layer `box-shadow` reads as a sticker.

Two things that are easy to get wrong:
- **Text glow goes on the text, not a wrapper.** `text-shadow: var(--mg-glow-text)`.
- **Glass tiles are lit from below.** The rim is brightest along the bottom edge and the
  bloom sits under the tile. A tile with an even rim looks flat and generic.

---

## 6 · What this style never does

- **No emojis, anywhere.** Build a designed mark: a coral-asterisk doc icon, a CSS
  arrow or check, a flat purple pictogram in the tile style, a small SVG.
- **No typeset text as a support beat** — except the Point Stack (scene 3). Every other
  supporting beat shows a real resource in a `.mg-media` card.
- **No random humans as b-roll.** Only cut to a person when that person *is* the subject.
- **No full-bleed screenshots.** Real media is always an object on a stage.
- **No perfectly still frames.** If a scene is held, something drifts.
- **No hard cut without a sound.**
