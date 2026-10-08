# 08 — Data, charts & screenshots (the "proof")

The middle of a data slide should carry proof. Best → simplest:

**In this style every proof sits in glass:** screenshots get a frosted glass frame, numbers get a
glass card. Prefer sources that are already dark — a light screenshot is a bright rectangle in a
void-black slide, so crop it tight and keep it small, or redraw the numbers as `bars`/`stats`
instead. Bar fills and stat numbers glow teal; the digits themselves stay moon white.

## 1. Real screenshots (most credible)
Grab the actual chart/tweet/thread and place it **big, framed, in the middle**, with a
**source caption** (e.g. "via anthropic.com"). Always attribute; only use content you can share.
- **Manual:** screenshot the chart, crop it tight, drop it in your design tool in a rounded white card.
- **Automated (skill):** `capture.py` screenshots a URL/region with Playwright.
- **Pro tip for stubborn sites** (charts inside carousels/JS): pull the chart **image URLs straight from the page's HTML** and download the originals — usually far higher-res than a screenshot. (The skill does this.)
- Sites that block bots need a real browser (the skill uses a normal user-agent + a headless browser).

## 2. Code-drawn charts (`carousel_charts.py`) — pick the form by the data's job

| The reader must… | Use | Colour job |
|---|---|---|
| Follow a trend over time | `line` | one lit series (+ a muted dashed one for context) |
| Compare magnitude across categories | `column` | emphasis: one lit, the rest fog gray |
| See a before → after per item | `dumbbell` | muted "before" dot, lit "after" dot |
| Judge one ratio against a limit | `meter` | lit fill on a same-hue track |
| Compare 2–4 things quickly | `bars` | emphasis |
| Read a headline number | `stats` (+ optional `spark`) | not a chart — a stat tile |

**Never** a dual axis, never a pie, never a number on every point, never a hue per category —
this brand has no categorical palette (teal is light; type is moon white or fog gray only), so
identity comes from **emphasis + direct labels**, and magnitude from the single-hue teal ramp.
If a chart has 2+ series it carries a legend whose key is a mark, not coloured text.

## 2b. Old notes on code-drawn charts / stats (when there's no clean screenshot)
- **Bars:** compare 2–4 things; color the winner in your accent, label every value, cite the source.
- **Big stats:** one or two huge numbers + a label (e.g. "4–6 hrs → minutes").
- **Chips:** a short list of items (e.g. "Trial balance · P&L · Ledgers · Vouchers").
- Keep the number ACCURATE — verify from a primary source.

## 3. People / reactions
- A real tweet or a photo of the person quoted can be the middle visual (attributed).

## Rules
- **Verify every number** before it goes on a slide. Never invent stats.
- **Attribute** every borrowed screenshot with a small "via [source]" line.
- Match a chart to a fitting headline — don't slap an unrelated chart under a headline.
