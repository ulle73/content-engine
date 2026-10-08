# The ten scenes

Every beat in a motiongraphics edit is one of these. Assign one to each beat in
`PLAN.md` **before** authoring anything.

**The rotation:** never the same scene twice in a row · never hold one past ~25s ·
every scene change carries a transition **and** a sound.

⌁ But read the reference honestly: **Clean Face is 30–40% of the runtime.** REF-A holds
it for 8–12s at a stretch between graphic beats, and only cuts 20 times in 190 seconds.
Wall-to-wall graphics is the amateur read. The frame breathing between beats is what
makes the next one land.

---

## 1 · Clean Face
Full-frame camera, no graphics. The rest beat, the cold open, the turn, the CTA.
Carries a **slow push** (`scale 1.00 → 1.06`, linear) so it is never truly static.
Captions per the video's switch.

## 2 · Face + Floating Panels
⌁ REF-A 1:03. One or two **semi-transparent** screenshots float over the footage, each
with a small white label above it. They drift with parallax and slide out to opposite
sides. Transparency (~60%) is what keeps the face readable — an opaque panel here just
becomes a split-screen and loses the layered feel.
- Panels enter from and exit to **their own side**. Never cross the frame.
- Keep them out of the face's centre third.

## 3 · Face + Point Stack
⌁ REF-A 1:36. The one sanctioned text-only support beat. A **violet headline** builds
word by word at the top-left, then **white bullet lines** stagger in beneath it, each
entering blurred and resolving. Lives in the **left third** (`96,300 → 800,860`); the
speaker keeps the right. Exits as a whole stack, blurring out together.
- 3–4 bullets maximum. Each is a short clause, not a sentence.
- Use it for an argument or a list of failures — the things that have no screenshot.

## 4 · Face + Stat Card
⌁ REF-A 0:20. A glass card with a small circular avatar, a handle with a verified tick,
and a big number that **counts up**. Placed beside the speaker's gesturing hand and
sliding in from that side.
- The number counts **after** the card lands (the late-second-beat rule).
- Real numbers only, verified while sourcing.

## 5 · Face + Brand Lockup
⌁ REF-A 1:52. Real brand marks in a lower-third lockup, bottom-left, entering with a
blur-in and **holding long** — 10–15s, far longer than any other graphic. Use it when a
whole section is about a named tool or a partnership. Marks must be the real logos;
never re-typeset a wordmark.

## 6 · Diagram Takeover
⌁ REF-A 0:28–0:58. The centrepiece, and the longest hold in the style. On `.mg-bg-field`:
1. Hard cut to the empty gear field, **held ~4 frames**.
2. A **section title builds word by word and lands LARGE**, while the line re-centres.
3. **The camera starts pulling back and never stops** — one unbroken zoom-out across the
   whole 30 seconds (`motion-grammar.md`). Everything below happens underneath it.
4. Panel 1 outlines in; its documents arrive **one at a time, ~0.34s apart, each landing
   grey and then colouring in**.
5. Panel 2 below: pills land on a stagger, connectors draw *after* their destination pill.
6. Panel 3 — **the loop**. A thick violet ring **draws itself** over ~1.6s, and a mark
   plus its label lands inside it once the ring has closed.

**Three panels, not two.** Budget 25–35s and let it build — one of the few places a long
hold is correct, because something new arrives every second or two and the camera is
moving the whole time.

## 7 · Slam Card
⌁ REF-B 0:25, 0:46. On `.mg-bg-bloom`: one **slam headline** in a wiping magenta bar,
plus **one hero media** in a `.mg-media` card. Nothing else. The payoff scene.
- The media card **grows slowly** the whole time it is held.
- Optionally a late-arriving stat mark or conic ring beneath.
- Reached through a **light leak**, not a cut.

## 8 · Screen Stage
⌁ REF-A 1:17, 2:10. Real screen recording as a **rimmed `.mg-media` card** on
`.mg-bg-rails` — never full-bleed. Enters small and blurred from below, settles, then
the camera **punches in on the region where the cursor is working** and follows it.
- Camera bubble optional, bottom-right, at the reserved box.
- Callouts are small labels and thin arrows only — never a card that hides the screen.
- Captions **off** during demos; the picture already says it.

## 9 · Object Stage
⌁ REF-B 0:35–0:45. **A two-act scene** on `.mg-bg-bloom`, with the camera pulling back
throughout act one.

**Act 1 — the figure.** A rim-lit figure anchors the frame (`.mg-figure`: a sphere head
with two soft white vertical ovals for eyes, an egg torso, a crescent highlight along the
top edge of both, and a wide halo). **Translucent** tiles (`.mg-tile-glass`) arrive **one
at a time, ~1.2s apart, at different positions and depths** — scattered around the figure,
never lined up. Each keeps its own scale so it reads at its own distance.

**Act 2 — the row and the dive.** The figure and its tiles clear in 3 frames. Three
**solid** tiles (`.mg-tile`) take the stage in a row and the camera **dives along it**: a
push-in that *also tracks laterally*, travelling past the first two to land on the third,
then pulling back out. ~2.4s in, ~1.0s back.

**The two tile treatments are not interchangeable.** The floating tiles are translucent
and rim-lit from **above**; the row tiles are solid and rim-lit from **below**. The key
light moves between the acts, and matching each rim to it is what makes them read as
objects rather than stickers.

Act 1 suits a subject surrounded by its context; act 2 a set of peer concepts. Either
half works alone. One dive per video, maximum — it is a loud move.

## 10 · Persona Circle
⌁ REF-A 2:40. The camera masked into a **circle with a glowing violet ring**
(`.mg-cam-circle`) on `.mg-bg-ribbon`. A quote types in line by line beside it; the
quote clears; the circle re-centres and scales down; a **name types in** below it.
Use it for a customer, a persona, a testimonial, or a direct-address aside.

---

## Assigning scenes in `PLAN.md`

For each beat record: **in/out word onsets** (from `transcript-tight.json`), the
**scene**, the **media** it needs, and whether it is a **re-hook**. A beat with no
assigned media that is not scenes 1/3/10 is not ready to build.

Plan a **re-hook every 45–90s** — an open loop, a pattern interrupt (scene change +
light leak + sound), or a tease of what's next. Mark them on the timeline before you
build, not after.

A rough chapter shape that works:

```
Clean Face  →  light leak  →  Diagram Takeover  →  leak  →  Clean Face (8s)
   →  Screen Stage  →  whip  →  Face + Point Stack  →  Clean Face
   →  leak  →  Slam Card (the chapter payoff)  →  Clean Face
```
