# BLACKLIST — things that never go in a short

> **⚠ 2026-08-27 — FOUR OF THESE ARE HOUSE-ONLY.** There are two styles now
> (`reference/STYLES.md`). Everything here applies to **house**. In the **persa** style,
> rules **#2b · #7 · #11 · #12** are deliberately suspended — they describe the cream-plate
> format, not the craft. Every other rule below applies to both styles, including #9 (do not
> redesign the CTA) and #4 (no emojis). Each of the four is annotated inline.


Every entry here came from Jad rejecting it on a real cut. This is a hard list: if a beat needs
one of these, the beat is wrong, not the rule. Check a cut against this **before** rendering.

---

## 1 · Small text — in ANY form
**Added 2026-08-10, on tp-0809 beat 04.**

> "I never want to see a short text as if you took a screenshot… even screenshots on the
> internet, I never want to see a small text that small. It just doesn't make any sense."

Banned outright:
- A screenshot of a **docs page, article, table, changelog or README** whose body type is small.
- A cropped **headline card** dropped on the plate (the "Message your other Claude Code sessions"
  card was the exact offender).
- Any **table** of body text. Three columns of 14px type is unreadable on a phone no matter how
  you scale it.
- Small captions/labels baked **inside** a screenshot.

The old "crop to the one story so it scales 1.15–2.33× up" rule is **not a licence to show text
screenshots**. It only applies to a genuinely large headline that already dominates its frame.

**What to do instead:** show the *meaning* as a designed, animated scene — mascots, real product
UI at readable scale, a diagram. If the only way to make the point is a wall of text, the point
belongs in the VO and the caption, not on screen.

## 2 · Typeset text cards as support
A card you set in type is not media. Every supporting beat is a real resource or a designed
scene. Captions are the only text that stays; the CTA pill is the single exception.

## 2b · Media in a frame, on a card, or with a drop shadow
> **HOUSE-ONLY.** persa's floating-window treatment is a real app window *with* a drop
> shadow over the live take (reel A, 32–38s). A card behind a page shot on a plate stays banned.
>
> **tierlist suspends it FOR THE TIER CARD ONLY** — a tier card *is* a white rounded plate with
> a drop shadow, and that is the object being reproduced. Everything else on the board still
> obeys this rule.

**Added 2026-08-10.**

> "why does the Claude Code one look weird — it looks small and there's something around it,
> like a shadow. I want it to be IN the page instead. Not only for Claude Code, for everything."

Media sits **in** the frame. No card behind it, no border, no rounded-corner plate, no drop
shadow, no inset padding that shrinks it. Those read as a sticker pasted onto the plate and they
make the asset look smaller than it is. Fill the slot with the thing itself.

The coral half is not an exception — the half ITSELF is coral and the media sits on it edge to
edge, which is not the same as a coral frame around a picture.

## 3 · Captions with their own background band
**Added 2026-08-10, on tp-0809 beat 06.**

> "why does the caption look weird… it has its own background and it looks really weird"

A caption must sit **on** the frame, not on a strip pasted over it. No full-width scrim, no
white band, no plate behind the words. If a caption isn't legible on the beat behind it, change
the caption **colour or position**, or darken the *media* — never introduce a band.

## 3b · Browser chrome on a page shot
**Added 2026-08-10.** No URL bar, no traffic-light dots, no site breadcrumb or sticky nav in a
page screenshot. The frame is the content. `scripts/shoot-page-9x16.py` strips every
`position:fixed` / `sticky` element at capture; `page-highlight.html` has no chrome at all.

Two more from the same note: the marker is **opaque ink** drawn across the words, never a
rounded translucent selection box — and the push **zooms into the marker**, anchored to the
bounding box of the highlight bars and clamped so the line can't leave the frame. A zoom that
pushes into the middle of the page while the highlight drifts off is wrong.

## 3c · More than one highlight at a time
**Added 2026-08-10.**

> "you should not have multiple things highlighted at the same time — we can only highlight one
> thing, not one word, but like an entire paragraph or sentence, but not multiple highlighters."

**One mark on screen.** The unit is a sentence or a paragraph, never a lone word and never two
separate marks. When that one sentence WRAPS, its lines are still one stroke: the second line
starts the instant the first finishes, the way a pen carries on. `page-highlight.html` enforces
this — it draws only the first phrase and warns if more are supplied.

The framing is solved at CAPTURE, not at layout: `shoot-page-9x16.py` centres the highlighted
phrase in the frame, so a split or transparent slot can sit on it without exposing blank page.

## 4 · Emojis
Anywhere on screen. Build designed marks instead: coral-circle monograms, CSS checks, arrows,
crosses, chips.

## 4b · A webcam bubble, or anyone else's screen recording
**Added 2026-08-10.**

> "I don't want to see a person in the bottom corner screen-sharing and talking — it has to look
> completely as if I did the screen share."

A clip with a presenter's face in the corner is **unusable**, not croppable. Also out: another
creator's burned-in captions, YouTube chrome/end cards, channel watermarks, cursor-trail
effects. And blogs are "mad boring" — go for real footage of the thing, a dashboard in motion,
a Reddit thread or an X post first. See `SOURCING.md`.

## 5 · People who aren't the subject
No stock footage, no podcast cutaways, no "generic developer at a laptop". Cut to a person only
when that person **is** the subject of the line. Otherwise the real UI or a designed scene.

## 6 · A screenshot of an animated block
Every block in `ui-blocks/` animates. A still of one reads as a screenshot and he
will say so. Render it to mp4 with `scripts/block-render.py`.

## 7 · The same frame twice in a row
> **HOUSE-ONLY.** persa holds ONE treatment for an 18s demo spine while a live screen
> recording runs under it. The clock runs on treatment + content there.
>
> **tierlist suspends it outright** — the frame never changes for the entire video. Its clock
> runs on the board's CONTENT: a card presented and placed every 3–5s.

**The rotation is a change of CAMERA TREATMENT, not of graphic.**
Transparent and b-roll-on-cream are the *same frame* — swapping the graphic inside the top zone
does not count as a change. Four distinct frames: **transparent · full face · split screen ·
b-roll full**. Never two neighbours alike, never hold one past ~8s.

## 8 · A silent layout change
Every layout change carries a transition **and** a sound. No exceptions.

## 9 · A new CTA
The CTA is the old one from `buzz` / `carousels` / `mcp`: logo chip, product name in mono,
COMMENT + "KEYWORD" in Instrument Serif italic, plain ink arrow. Do not redesign it.

## 10 · The graph-paper plate
Tried 2026-08-07, rejected 2026-08-08. The plate is flat `--cream` (#F0EDE4). White is the
exception for a *captured* device.

> This fixes the **house** plate. It does not claim cream is the only ground in the skill —
> persa has no plate at all, and tierlist's ground is flat black `--tier-void` (#0B0B0B),
> because five saturated row colours and white cards need a dead ground to read against.

## 11 · Shrinking him
> **HOUSE-ONLY.** In persa, shrinking him into the camera card IS the treatment — though his
> head is still matted and pops out over the card's edge, which is this same pop-out technique.
>
> **tierlist suspends it too.** A fixed 1080×936 bottom-half crop for the whole video is the
> layout, not a shrink for a beat. And tierlist has **no matte at all** — the one style in the
> skill that never runs `rvm-matte.py`.

`--cut:1`. The transparent layout keeps him full size; slide him **down** to make room for media,
never scale him down. Never delete the pop-out.

## 12 · Captions on his body or over the b-roll
> **HOUSE-ONLY.** persa pins the caption at 72.9% — on his chest — in every treatment, on
> purpose, so the eye never has to re-find the line.
>
> **IN FORCE in tierlist.** Its band sits at 884–984, on the black void between the last row
> and the seam — not on him, not over media. This is where tierlist and persa differ.

Captions live in the 820–940 band on the pop-out layouts and on the seam in a split. Never
across his chest, never over the media in a b-roll beat.

## 13 · Publishing anything
Nothing is posted, uploaded or scheduled without explicit approval. Every edit ends at
"rendered, scored, opened for review."

## 14 · A NUMBER THAT IS THE WHOLE PICTURE
**Added 2026-08-18, on tp-0817b beat 15.**

> "I don't want just (animation) that look like just captions — I need actual nice animations
> with the 158 languages, not just text like that, because it just looks like captions. Do you
> see what I mean?"

The beat was a big coral **158** with **LANGUAGES** set under it, counting up from zero. It
passed every other rule — real figure, fact-checked, animating, house type, on the word — and
it is still **banned**, because a number that animates is text that moves. Setting a figure in
Montserrat 900 and counting it is a caption in a different font.

**The test: cover the digits with your thumb. Does the frame still mean anything?**
If the answer is no, the beat is a caption and there is nothing on screen.

**The rule: the number is an ANNOTATION on a picture of the quantity, never the subject.**
Build the thing the number counts, then let the figure ride on it:

| he says | not this | this |
|---|---|---|
| "158 languages" | `158` counting up | 158 real language marks flooding the frame, a wall assembling tile by tile, the figure riding on it |
| "28 million lines of the Linux kernel" | `28,000,000` counting up | real code mass filling the frame / file blocks stacking until they overrun it |
| "3,400 tokens vs over 400,000" | two typeset figures | two bars, one dwarfing the other, drawn — the *ratio* is the picture |
| "39,000 stars" | `39,000` counting up | stars actually accumulating (`star-rating-fill`) with the count as the label |

`count-up`, `number-wheel`, `number-pop-in` and a hand-authored counter are all the SAME
mistake in different type. They are labels for a scene, not the scene. `library/sections.json`
said "the figure ANIMATING — counting" and that wording was too weak; it now says this.

This is the same note as #2 (typeset text cards as support) and the mascot note — **a
transition applied to words is not an animation.** It is the third time it has been given.

## 15 · The Chrome caption
**Added 2026-08-20.**

> "let's change Chrome — I never want to see it ever again, turn it into Parallax"

The silver-gradient caption style (`.c-chrome`, Montserrat 900 on a
`linear-gradient(180deg,#FFFFFF,#CFCAC2,#8E8880,#FFFFFF)` with `background-clip:text`) is
**deleted**, not benched. Silver only reads against something dark, and the face beats it was
written for are a light shirt against a light wall — it was invisible at tp-0817 15.0s and at
three sampled points on tp-0817b.

**Full-face beats take Parallax at `y1400`.** There are now THREE caption styles:
`c-par` · `c-ws` · `c-hl`.

It was removed from every `build.py` and every `index.html` in the corpus — the assignment
AND the CSS rule — so rebuilding any old video produces Parallax rather than resurrecting it.
Do not re-add it, and do not offer a "dark-background variant": he said ever again.

## 16 · A SCREENSHOT DROPPED INTO A BOX INSTEAD OF OWNING THE FRAME
**Added 2026-08-27, on the caption book beat 4. Applies to BOTH styles.**

> "you took a screenshot, right, and then you just fucking put it into the frame, makes no
> sense … Look how shitty it is. It's overlaying my face. It's small. It's not full screen.
> And I've seen you do that so many times."

**When a real UI is the beat, the UI owns the WHOLE FRAME — 1080×1920, corner to corner —
and HE goes on top as a cutout.** Never the media over his face. Never a page shot floating
in a partial box with a hard edge across him.

**The mechanical cause, and it is always the same two things:**

1. **The wrong box.** Our page shots are ALREADY shot at 1080×1920 by `shoot-page-9x16.py`.
   Putting one in a `height:1180px` box is squashing a full-frame asset into a strip.
2. **`object-fit: contain`.** With the wrong box, `contain` does not crop — it *shrinks the
   whole image until it fits*, so a 1080×1920 shot in a 1080×1180 box renders **664px wide**
   with dead space either side. That is the entire "small screenshot floating in the frame"
   look, and it passes every gate silently.

```css
/* RIGHT — the UI is the frame */
.uifull{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
/* and he sits in the card over it, head matted so it breaks the card's edge */
```

**`object-fit:contain` on a full-frame surface is nearly always the bug.** Use `cover`, and
give the element the box it actually deserves.

### 16b · And the text goes in the UI's real negative space
Once the UI owns the frame, a lime annotation typed at a guessed `top:` lands on the UI's own
headline or buttons. In the reels it never does — it sits in the black gutter of the curve
graph, in genuine empty space, aligned to the UI's grid.

**Measure it, do not guess:**

```bash
python scripts/find-empty-space.py <shot.png> --max-y 1143   # 1143 = the camera card's top
```

It prints the largest genuinely empty rectangle and the box to place text in. If the biggest
box is too narrow, **that shot is the wrong shot for an annotation** — a dense marketing page
has no negative space. `askrecord.png` offers only 400px wide; `fork.png` offers the full
1080×360. His works because a curve editor is mostly empty black.

---

## The test before you render
1. Scrub the beat list — does the **frame** change every beat?
2. Is there any text on screen that isn't a caption or the CTA pill?
3. Would you be able to read every screenshot at a third of 1080 wide?
4. Does every layout change have a sound?
5. Is every animated block a video, not a still?
6. **Thumb over every number on screen — does that frame still mean anything?** If not, you
   have built a caption and called it a graphic (#14).
7. Any `c-chrome` anywhere? There are three caption styles, not four (#15).
8. **Is every real-UI beat FULL FRAME with him on top — or did a screenshot end up in a
   box, shrunk by `object-fit:contain`, with a hard edge across his face? (#16)**
