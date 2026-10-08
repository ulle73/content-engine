# Typography

Two faces. Two jobs. There is no third tier, no label, no chip, no lower
third, no number treatment. Adding one is how this style stops looking like
itself.

---

## 1 · The title line — a Didone serif

**Playfair Display, weight 400, ≈56px @1920h.**

Identified by fitting candidates at matched glyph height against the measured
string `the definition of work-life balance:` (878px wide, 45px ascender-to-
baseline):

| Candidate | Size at matched height | Width | Error vs 878 |
|---|---|---|---|
| **Playfair Display** | 56px | 872 | **−6** |
| Bodoni Moda | 57 | 910 | +32 |
| Lora | 57 | 914 | +36 |
| Libre Baskerville | 53 | 938 | +60 |
| DM Serif Display | 62 | 951 | +73 |
| EB Garamond | 61 | 798 | −80 |
| Instrument Serif | 59 | 703 | −175 |

Playfair matches to 0.7%, and the shapes agree: high stroke contrast, vertical
stress, hairline serifs, ball terminals on `f`, `r`, `a`, `c` (`stills/04` at
3×). It is a Google font, so it ships without a licensing question.

Set it: **sentence case, no tracking** (measured +0.003em, i.e. none), pure
white, one line, ending in a colon. The colon is doing real work — it frames
whatever the speaker is about to say as the answer.

## 2 · The caption — a tight Helvetica-family bold

**≈63px @1920h, tracking −0.065em, weight 700, pure white.**

Measured: x-height 36px, ascender 48px, baseline at y=1042, and the string
`sunshine and rainbows` exactly 624px wide.

The source face is a Helvetica-family grotesque — the `a` carries a spur, the
`e` terminal is horizontal, and Helvetica Bold needed the least tracking
correction of any candidate to reach the measured width. **Inter is the
substitute the tokens ship**, because it is already in the house and licensed
cleanly. Calibrated in-browser, Inter Bold at 63px / −0.065em renders that
string at 626px against the measured 624 — a 0.3% error.

**The tracking is not a taste call.** At default spacing every candidate face
was 100–180px too wide over 21 characters. It really is set that tight; the
letters nearly touch. It is most of what makes the caption read as designed
rather than as a subtitle track.

If exactness ever matters more than portability, Helvetica Neue Bold is on the
Mac and can be vendored into the segment — at −0.055em, not −0.065em, because
its default spacing is tighter than Inter's.

## 3 · Sizing, and the trap

Sizes are in **`cqh`** — percent of the frame's height — so one scale serves
both canvases. `cqh` resolves against the nearest size container, which is why
the composition root **must** carry `.zk-frame`.

⚠ Without it, every string renders at a fraction of its intended size and the
layout still looks plausible. And never size type in `%`: a percentage
`font-size` resolves against the *parent's* font-size, not the frame, which
fails the same way and just as quietly. If a scene looks subtly wrong, check
this before anything else.

## 4 · 16:9

The title and caption do **not** scale down with the frame. `2.92cqh` would put
the title at 31px and the caption at 35px on a 1080-tall frame; both die in
compression, and a 16:9 video is watched across a room rather than at arm's
length.

The caption size in 16:9 is the one token in the whole style that was **chosen
rather than derived** — the window changes aspect, so the two candidate rules
disagree by 3×. See the note in `assets/tokens.css` §16:9 and `layouts.md` §5.
Change it by looking at a render, never by arithmetic.
