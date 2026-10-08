# Long-form STRUCTURE — the arc, the chapters, the retention curve

**Read this before anything else.** A short is one 45-second ramp; a long-form video is a
sequence of ramps with deliberate re-entry points. Structure is not a nicety here — it is the
single biggest lever on retention, and it must be agreed **before** a frame is authored.

---

## 1 · The arc

| # | Beat | Typical length | What it does |
|---|---|---|---|
| 1 | **COLD OPEN** | 0:00 – 0:15 | Show the payoff FIRST. The result, the number, the thing working. Real media + motion from second one. |
| 2 | **PAYOFF SPIKE** | on the punch word | Reveal + coral flash + the `riser` cresting. The fixed signature. |
| 3 | **PROMISE** | 0:15 – 0:45 | What they get, why now. Title card. Plant **one open loop**. |
| 4 | **CHAPTERS 1…N** | 60 – 180s each | 3–6 of them. Each opens on a chapter card and runs its own mini-arc. |
| 5 | **RE-HOOKS** | every 45 – 90s | Scattered through the chapters. See §3. |
| 6 | **THE TURN** | ~65–75% in | The catch. Full-frame face, Face Punch, graphics cleared, music drops. |
| 7 | **RECAP** | last 60 – 90s | The numbered payoff, one staggered line per chapter. |
| 8 | **CTA / OUTRO** | last 15 – 25s | The ask + the next-video card. |

### The cold open is not an intro
Banned openers: "hey guys", "in today's video", "before we start", a logo sting, a channel
intro, and a lone static title. The first frame either **shows the end state** or **poses the
question the video answers**. If the recording opens with a greeting, cut it — the tighten pass
gives you the timeline to do that cleanly.

### Every chapter is a small video
```
chapter card (~2s)  →  the CLAIM (what I'm about to show you)
                    →  the PROOF  (real media — the UI, the repo, the page, the number)
                    →  the DEMO   (screen-share, or a designed explainer)
                    →  the TAKEAWAY (one line, one graphic, then move)
```
A chapter that is only a claim and a takeaway has no reason to be a chapter — fold it into its
neighbour. A chapter running past ~180s wants splitting.

### The turn
Every video needs one honest reversal placed roughly two-thirds through: the limitation, the
cost, the thing that breaks, the case where it does not apply. It is the highest-retention beat
in the whole video **and** it is what keeps the edit truthful. Treat it as a structural
requirement, not an optional aside. If the recording contains no caveat, say so in the plan
rather than inventing one.

---

## 2 · The retention budget

Hard numbers. Check the plan against them before building.

| Rule | Limit |
|---|---|
| A new visual beat | at least every **8s** |
| Uninterrupted talking head (no cut/zoom/graphic/b-roll) | max **12s** |
| The same layout on screen | max **25s** |
| A re-hook | at least every **90s** |
| A chapter | 60–180s |
| One support graphic on screen | max **10s** (then evolve it) |
| Dead air after tightening | max **0.55s** between words |

**The first 30 seconds carry the whole video.** Budget disproportionate effort there: the best
media, the tightest cuts, the layout rotation at its fastest.

---

## 3 · Re-hooks — the four kinds

Place one every 45–90s. Vary the kind; the same device three times stops working.

1. **Open loop** — name something you'll pay off later. "One of these three is going to cost
   you money — I'll tell you which at the end." Must actually be paid off; an unpaid loop is a
   bait-and-switch and will read as one.
2. **Pattern interrupt** — a layout change + a transition + a sound, with no narrative reason.
   Cheapest to build, works, but only ~2–3 per video before it feels mechanical.
3. **Forward tease** — a 1–2s flash of a later beat ("this bit is why I made the video") with a
   `whoosh` and a quick blur-in.
4. **Escalation** — the number goes up, the stack gets taller, the list gets longer. The
   graphic itself carries the hook.

Mark every re-hook in `PLAN.md` with its timestamp and kind, **before building**.

---

## 4 · `PLAN.md` — the artifact you get a "go" on

Produce this from the tight transcript, show it, and wait for approval before authoring. On a
15-minute video, building before the structure is agreed wastes hours.

```markdown
# <video name> — plan
Source: assets/recording-tight.mp4 (14:22) · transcript-tight.json

## Chapters
| # | Title | IN (word @ t) | OUT (word @ t) | Dur | Layout opener | Proof media |
|---|---|---|---|---|---|---|
| 0 | Cold open      | "three"  @ 0:00.4 | "free"    @ 0:14.8 | 14.4s | Transparent | orca OG card |
| 1 | What it does   | "so"     @ 0:45.1 | "queue"   @ 2:31.6 | 106s  | Split L     | real UI clip |
…

## Re-hooks
| t | kind | what |
|---|---|---|
| 1:12 | open loop      | "one of these is a trap" |
| 2:48 | forward tease  | flash of the pricing page |

## The turn
7:40 — "here's the catch: it only works locally" — Full-Frame Face, Face Punch, bed drops.

## Media shopping list  (need ≥ 1 per 25s → 35 items)
| # | beat @ t | what | source | got? |
|---|---|---|---|---|
| 1 | 0:02 | orca repo OG card | opengraph.githubassets.com/… | ☐ |

## Captions ON at
0:00–0:15 (cold open) · 3:02–3:09 (the stat) · 7:40–7:58 (the turn) · outro

## Segments to render
seg-01-cold-open · seg-02-what-it-does · … · seg-08-outro
```

---

## 5 · The timing table (per segment, before rendering)

Same instrument as the short, one table per segment. Every graphic gets a row.

| # | IN (word @ t) | OUT (word @ t) | Dur | Element | Layout / zone | Enter → Exit |
|---|---|---|---|---|---|---|
| 1 | "banned" @ 1:03.2 | "worldwide" @ 1:07.0 | 3.8s | headline slam | Split L / media | rise → fade-up-out |
| 2 | "$300" @ 1:11.5 | "minutes" @ 1:14.1 | 2.6s | cost count-up | B-Roll / full | scale-in → shrink-out |

Rules the table enforces: no row longer than 10s · no two rows overlapping in the same zone ·
every row has an entrance **and** an exit · nothing in a reserved lane · every IN is a real word
onset from `transcript-tight.json`, never a round number.

**SFX are not planned here.** Sound is a separate pass on the locked render (`sound-design.md`).

---

## 6 · Chapters as a deliverable

YouTube chapters need a `0:00` first entry and each chapter ≥10s. `scripts/concat-segments.sh`
writes `out/chapters.txt` from the real rendered segment durations — never hand-count them,
and never copy them from `PLAN.md` (the plan's times are pre-render estimates and will drift).
