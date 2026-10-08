# Typography

Four faces, four jobs. Nothing else gets set.

| Job | Token | Face | Where it came from |
|---|---|---|---|
| Word caption | `--pa-font-caption` | **Inter 700**, caps | matched to the reference |
| Emphasis / slam | `--pa-font-display` | **Anton** (→ Impact) | matched; Impact named by reel C |
| Hand note | `--pa-font-hand` | **Gochi Hand** (→ Caveat Brush) | matched to the reference |
| Chips, lower third | `--pa-font-ui` | **Inter 500** | matched to the reference |

---

## 1 · How these were chosen, and what is uncertain

Each reference face was cropped at 2–4× (`stills/07`, `08`, `09`), then candidate
fonts were rendered at matched cap-height and compared letterform by letterform.

**The originals are not identified.** These are the closest freely-licensed,
web-embeddable matches, chosen on letterform evidence:

- **Caption** — reference shows a neo-grotesque Bold: straight splayed `R` leg,
  equal `E` arms, vertical-sided `M`, generous counters. Inter Bold matches on all
  four. Helvetica Neue Bold is the native alternative and is also very close;
  Poppins Bold is not (its `M` splays).
- **Display** — extreme weight, condensed, slit counters, `G` with a flat spur.
  **Impact** and **Anton** are both near-exact; Bebas Neue and Oswald are far too
  light, Archivo Black too wide. Anton is the token because it embeds as a webfont;
  Impact is on every Mac and is the truer reference.
- **Hand** — *upright* (not slanted), even rounded felt-tip strokes, mixed cap and
  small-cap heights, `o` a small circle. That rules out Permanent Marker and
  Sriracha, which both slant. **Gochi Hand** matches the proportions best;
  **Caveat Brush** matches the weight better and is the alternate.

If an exact licence for the originals turns up later, swap the token — nothing
else in the skill depends on the specific file.

---

## 2 · The scale

All sizes are a **percentage of frame height**, so one sheet serves 9:16 and 16:9.

| Token | % of height | @1920h | Measured cap-height |
|---|---|---|---|
| `--pa-cap-size` | 2.75% | 53px | 38px |
| `--pa-emph-size` | 11.0% | 211px | 153px |
| `--pa-slam-size` | 9.5% | 182px | — |
| `--pa-hand-size` | 3.4% | 65px | — |
| `--pa-chip-size` | 1.5% | 29px | — |

**The emphasis word is 4× the caption.** That ratio is the style's whole sense of
hierarchy — there is no middle tier. Do not invent one.

Nothing below ~1.4% of frame height survives platform compression.

---

## 3 · Rules

- **ALL CAPS** for caption, emphasis and slam. The hand note is the only
  mixed-case text, and the reference sets it in sentence case.
- **Tight tracking on display** (`-0.01` to `-0.02em`). The reference's letters
  nearly touch. Default tracking on a heavy condensed face looks unset.
- **One accent per frame.** Red *or* lime *or* amber. Two is a collision.
- **Never a text box, badge or highlight bar** behind a caption. The halo is the
  entire treatment. (Chips are different — they label an app, not a caption.)
- **Never an emoji.** Build a designed mark: a CSS glyph, a small SVG, a monogram.

---

## 4 · The font shelf (from the third reel)

The third link is a **different creator** and a different look — it is a
recommendation reel, not a style reference. What it is good for is its font
picks, which are worth having on the shelf for slam cards and thumbnails:

| Font | Use | Availability |
|---|---|---|
| **Impact** | bold compressed slam headline | ships with macOS |
| **Snell Roundhand** | script contrast against heavy caps | ships with macOS |
| **Rocktown** | brush/marker display | **commercial — must be licensed** |

⚠ Rocktown is not free. Do not put it in a monetized client video without a
licence. `--pa-font-hand` covers the same job with a licence we have.

⚠ That reel's own layout — yellow display type, red frames, a black bar under the
speaker, sentence-case serif captions in a bottom band — is **not** persa. Do not
mix it in. Its contact sheet is kept as `stills/14-reelC-fonts-contact-1fps.jpg`
only so the font names are traceable to their source.
