---
name: nextphase-studio
description: >-
  Router för NextPhase Skill Pack (kit `nextphase` i content-engine). Använd när användaren vill redigera en talking-head-inspelning i en NextPhase-stil – short 9:16 (house, persa, tierlist) eller long 16:9 (nextphase coral, motiongraphics, persa, vibecode, zak) – eller när `studio` pekat hit. Frågar format + stil (om det inte redan är sagt) och lämnar över till rätt stilskill.
---

# NextPhase Studio — the router

> **Importerad till content-engine — kit `nextphase` (NextPhase Skill Pack).**
> **Varumärke:** Stilarna har Claude-/AI-nyhetscopy och färger som standard. Teknikerna är det värdefulla — copy, loggor och färger är utbytbara (färgerna sitter i `assets/tokens.css`). Biblioteksanvändaren är som standard **Golfkuponger** (svensk golf, svensk text; se `skills/golfkuponger-brand/`) — byt gärna till dess färger och ton, men inget här är en spärr. Kitets "hard rules" och husregler beskriver hur originalstilen ser ut; se dem som förval och tips, inte krav. "Jad/han" i texten = originalskaparen, för oss = användaren.
> **Husregler:** kitets `CLAUDE.md` finns som valfri vägledning i `library/kits/nextphase/reference/nextphase-house-rules.md`.


This pack contains **six editing skills**. They share a pipeline (transcribe →
tighten → plan → build → render → sound) and differ only in **design system and
scene vocabulary**. Picking the wrong one wastes the whole build, so the pick is
step 0 — **before transcribing**, before sourcing, before anything.

---

## Step 0 — ASK. Every time. Never infer.

Ask both questions **in one go** (skip what the user already said), using the AskUserQuestion tool if you have it.
Never guess the format from the footage's aspect ratio and never guess the style
from the content. If the person named the style themselves in the same message
they dropped the recording ("the tier list one", "do it in zak", "the cobalt one"),
skip that half of the question and confirm it back in one line.

### Question 1 — what are we making?

| answer | canvas | goes to |
|---|---|---|
| **Short format** — TikTok / Reels / YouTube Shorts, 15–60s | 9:16 · 1080×1920 | `nextphase-short-editing` |
| **Long format** — a YouTube video, 5–20 min | 16:9 · 1920×1080 | one of the five long styles |

### Question 2 — which style?

**If they said SHORT**, the style lives inside `nextphase-short-editing` and there
are three. Read `library/kits/nextphase/skills/nextphase-short-editing/reference/STYLES.md` before you build —
two of them have a precondition that can veto the choice.

| style | the look | precondition |
|---|---|---|
| **house** *(default)* | camera as a matted pop-out on a cream plate; the frame changes every beat | none |
| **persa** | full bleed — the camera **is** the frame, graphics change over a continuous take | needs a real product demo worth 15s+ of screen time |
| **tierlist** | nothing moves; a tier board owns the top half, camera owns the bottom, cards land on the beat | the transcript must actually rank 4+ named things |

**If they said LONG**, there are five, each its own skill folder:

| style | skill | the look |
|---|---|---|
| **nextphase** | `nextphase-long-editing` | coral on a dark dotted grid; cards, chapter wipes, article highlighters |
| **motiongraphics** | `motiongraphics` | violet/magenta glow; lit glass tiles, self-building node diagrams, slam headlines on wiping bars, light-leak transitions |
| **persa** | `persa` | warm desaturated film grade over the raw footage; hard-cut one-word captions; the subject matted back on top so the head occludes the big words |
| **vibecode** | `vibecode` | saturated cobalt under cut-paper collage; a fake editing timeline on ruled paper that builds clip by clip; scissored screenshots; hand-drawn red X marks; stop-motion churn on 2s |
| **zak** | `zak` | a rounded window floating on pure black with equal air above and below; one Didone serif line; tight white 2–4 word captions hard-cutting inside the window; nothing moves at all |

If they're unsure, ask what the video *is* and recommend one — don't make them
read the table. Rough guide: a news/how-to explainer → **nextphase**; something
technical and premium → **motiongraphics**; a personal talking-head with real
screen demos → **persa**; a build/coding video → **vibecode**; a quiet, serious
monologue → **zak**.

> **Vertical long-form?** `persa` and `zak` were both measured at 9:16 and ship a
> real 9:16 form. The other three are 16:9 designs — say so before you commit.

Write the answer at the top of `PLAN.md` before you do anything else.

---

## Step 1 — read the whole style skill

Once the style is picked, read that skill's `SKILL.md` **and every file in its
`reference/`** (`library/kits/nextphase/skills/<skill>/reference/`) before building. These are measured design systems, not mood
boards — the numbers in them are the deliverable. Do not mix two styles' tokens
in one composition, ever.

## Step 2 — build it

Follow the style skill. It owns the structure, the scene list, the motion
grammar and the sound pass. The pack's shared house rules (originally its `CLAUDE.md`) are kept as optional
guidance in `library/kits/nextphase/reference/nextphase-house-rules.md`.

## Step 3 — deliver

Deliver the rendered, scored video and open it for review. **Nothing publishes or
uploads without the person explicitly approving it.**
