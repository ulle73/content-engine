# Slide recipes

A live carousel has an arc: **hook → value → value → CTA**. The default is 4 slides, and 3 to 7 all
work. Each slide is 6 s (3 bars) or 8 s (4 bars). The hook can be 6 s, because it should hit fast.

## What the reference template does (study it before writing your own)

| slide | file              | dur | the one big moment                                                                                     |
| ----- | ----------------- | --- | ------------------------------------------------------------------------------------------------------ |
| hook  | `01-hook.html`    | 6 s | The frame looks dead still ("0 FPS"). The ball crashes in, hops across S·T·A·T·I·C, the word flips letter by letter to ALIVE., and the beat drops. Tape-stop, then it flips back to STATIC. |
| value | `02-easing.html`  | 8 s | Two lanes: a hollow LINEAR ball against the eased ball, with spacing ticks and curve icons. Then a marker strikes out LINEAR. |
| value | `03-weight.html`  | 8 s | The ball bounces on the word WEIGHT. with a decaying rhythm and stretches and squashes. The word squashes too, through its width axis. |
| CTA   | `04-cta.html`     | 8 s | The ball snaps into the dashed O of M●TION. A comment bar types MOTION, a cursor presses Post, and a reply bubble pops up with hearts. |

Each file is about 400 to 600 lines. Copy the closest one as the starting point for a new slide and
keep its chrome.

## Find the protagonist (the concept move)

Pick **one object** that belongs to the topic, can move physically, and can prove each point by what
it does. It travels through every slide: it exits right and enters the next slide from the left.

| topic                 | protagonist                    | how it teaches                                       |
| --------------------- | ------------------------------ | ---------------------------------------------------- |
| motion design         | a bouncing ball                | easing, weight, squash and stretch                   |
| personal finance      | a coin                         | it rolls into a jar, compounds (splits in 2, then 4), drops through a fee slot |
| productivity          | a checkbox / task card         | it gets ticked, stacked, or batched into one card    |
| fitness               | a kettlebell / plate           | it is heavy, so the type sags; reps rendered as a beat |
| UX / product          | a cursor                       | it hesitates, misclicks, finds the button            |
| marketing / funnels   | a droplet                      | it falls through the funnel and leaks at the weak step |
| AI / automation       | a spark / cursor that types    | it writes the BIG WORD itself, letter by letter       |
| writing / hooks       | a caret `|`                    | it deletes the weak word and retypes the strong one   |

If nothing physical fits, the protagonist can be the BIG WORD itself. The letters can fall,
squash, shuffle into place or flip.

## Hook patterns (slide 1, the first 0.5 s decides the swipe)

- **Dead → alive**: the frame looks static or wrong, then the protagonist crashes in on the downbeat
  and changes the word. (This is the template.)
- **Contradiction**: the BIG WORD states the common belief, and the protagonist knocks a letter out
  so the word becomes the truth. For example, POST MORE becomes POST LESS.
- **Number slam**: a count-up that overshoots and settles on the stat, and the word squashes on landing.
- **Split screen**: their way on the left and the right way on the right, with the same object moving
  in both lanes.
Always hit something within 0.5 s, and show a "swipe" nudge near the end of the loop.

## Value patterns

- **Demo, don't tell**: the object performs the rule. Put the BIG WORD on the wrong way (LINEAR.)
  and strike it out as the right way plays.
- **Compare lanes**: two tracks show the same distance in the same time with different spacing.
  Stamp ticks every 2 frames so the difference is visible.
- **Before / after wipe**: a vertical wipe across the same layout as the object passes.
- **Annotated slow-mo**: strobe ghosts (a chronophotograph) plus 2 or 3 callouts drawn with leader
  lines (STRETCH = speed, SQUASH = impact).

## CTA patterns

- **Comment keyword**: the object becomes a letter of the keyword. A comment bar types it, a cursor
  presses Post, and the reply bubble ("sent ✓ check your DMs") pops up with hearts.
- **Save**: the object drops into a bookmark icon that fills.
- The bottom triplet carries the secondary asks: `SAVE · SHARE · FOLLOW FOR PART 2`.
- Reset everything before the loop point. The object hops out to the right, back to slide 1's world.

## Continuity tricks that make swiping feel like one film

- The object exits right at the end of slide N and enters from the left at the start of slide N+1.
  Match the height and speed.
- One **timeline ruler** across all slides: set `frameStart` = the sum of the earlier slides' frames.
- The same 120 BPM groove on every slide. Each slide is whole bars, so the beat never stumbles across a swipe.
- Keep the counters `01 / 04` … `04 / 04` in the top bar.

## Pacing on the beat grid (120 BPM, beat = 0.5 s, bar = 2 s)

- Put big impacts on downbeats (0.0, 2.0, 4.0 …) and secondary hits on beats.
- Let letter-by-letter sequences run on eighths (0.25 s) or sixteenths (0.125 s).
- Leave the last 0.5 to 0.8 s for the reset and the exit, so the loop point is calm.
