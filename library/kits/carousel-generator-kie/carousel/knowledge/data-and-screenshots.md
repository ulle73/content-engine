# 08 — Data, charts & screenshots (the "proof")

The middle of a data slide should carry proof. Best → simplest:

## 1. Real screenshots (most credible)
Grab the actual chart/tweet/thread and place it **big, framed, in the middle**, with a
**source caption** (e.g. "via anthropic.com"). Always attribute; only use content you can share.
- **Manual:** screenshot the chart, crop it tight, drop it in your design tool in a rounded white card.
- **Automated (skill):** `capture.py` screenshots a URL/region with Playwright.
- **Pro tip for stubborn sites** (charts inside carousels/JS): pull the chart **image URLs straight from the page's HTML** and download the originals — usually far higher-res than a screenshot. (The skill does this.)
- Sites that block bots need a real browser (the skill uses a normal user-agent + a headless browser).

## 2. Code-drawn charts / stats (when there's no clean screenshot)
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
