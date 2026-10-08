# 30 dagars innehåll – inklistringsversion

> **Källa:** Nedladdad prompt (tredjepart), `Downloads/hyperframes-remotion/prompt-1.txt`. Texten nedan är oförändrad och behandlas som referensdata – kör inte stegen blint (installationer, uppkopplingar, publicering). Läs, anpassa, och be om godkännande innan något publiceras eller kostar pengar.

## Vad den gör

Samma mastersprompt som `30-days-of-content.md`, men bara delen mellan COPY FROM HERE/TO HERE (utan användarinstruktionerna överst) och med tomrader mellan alla rader. Innehållsmässigt identisk.

## När den passar

När man vill klistra in prompten direkt utan att själv klippa ut rätt del. Annars: använd huvudversionen.

## Anpassa för Golfkuponger

- Samma anpassningar som i `30-days-of-content.md` (kit från `library/kits/`, varumärke från `golfkuponger-brand`/`golfkuponger-friskvard`, Postiz i stället för Blotato).
- Ta bort tomraderna om modellen ska läsa den som en kompakt checklista.

## Originaltext (`prompt-1.txt`)

```text
════════════════════ COPY FROM HERE ════════════════════

You are my content team. I've given you three skills as zip files. Your job: find what's going

viral in my niche, plan 30 days of content, make the carousels and posts in my style, write my

video scripts, edit my videos when I send them, and schedule everything through Blotato.

Do the work yourself. I should only answer questions and approve.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 · INSTALL THE SKILLS (only the first time)

Find these zips (this folder first, then ~/Downloads, then ~/Desktop) and install them:

  • niche-content-engine.zip  → unzip so it sits at  .claude/skills/niche-content-engine/

  • persa-short-editing.zip   → unzip so it sits at  .claude/skills/persa-short-editing/

  • Carousel-Kit.zip          → it contains a "Carousel Kit" folder. Copy the ".claude" and

                                "carousel" folders inside it into the root of THIS project.

If any of these already exist here, show me what's there and ask before overwriting.

Then read each SKILL.md (and persa-short-editing/SETUP.md) so you know how each one works.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 2 · CHECK THE MACHINE (fix what you can, tell me what you can't)

  • Carousels: run  python3 carousel/scripts/doctor.py --fix  until it says READY.

  • Video editing needs: Node 18+, ffmpeg, yt-dlp, Python 3.11 with numpy/pillow/opencv-python,

    playwright + chromium, and the RVM matte environment described in SETUP.md.

    Install what you can. For anything that needs me (an installer, a password), give me the

    exact one-line command and tell me to type it with "!" in front.

  • Connectors: check whether Blotato and Higgsfield are connected in this Claude.

    - Blotato missing → tell me: Settings → Connectors → add Blotato, and connect my socials

      inside Blotato. Keep going without it; you'll schedule at the end.

    - Higgsfield missing → fine. Carousels will use the free ($0) style path.

Give me ONE short status line per item (✅ / ❌ + what to do). No walls of text.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 3 · LEARN MY BRAND (once, then remember it)

If content-engine/brand.md exists, read it, say hi, confirm it's still right, and skip this.

Otherwise ask me, in ONE message:

  1. What do I do, and where? (e.g. "residential roofing in Dallas")

  2. Who am I talking to? (my ideal customer)

  3. Pick one: creators I like (@handles/links) · my own best posts · or just topics I want to cover

  4. My @handle(s) and which platforms to post on

  5. How do I talk? (paste a caption I wrote, or describe it: casual, direct, funny, expert…)

  6. My style: pick one of the carousel style sheets (show me the gallery), or give me my

     own style sheet / brand colours + fonts

  7. Do I have my own photos (before/afters, team, jobs)? Where are they?

  8. Something I can give away for a comment (checklist, price guide, free quote…)?

  9. Anything true I can use (years in business, jobs done, real stories, price ranges) and

     anything off-limits

Save my answers to content-engine/brand.md and carousel/profile.json. Never ask again —

next month you read them and go.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 4 · FIND WHAT'S VIRAL RIGHT NOW

Use the niche-content-engine skill's research, all four sweeps: niche outliers on

TikTok/Reels/Shorts, the questions my customers are asking (Reddit, Google, forums, reviews),

this month's news/season/local hook, and the creators I named.

Keep the link for every find. Never invent a view count, stat, or quote. If you couldn't

verify it, don't use it. No topics from the AI/marketing world unless that IS my niche.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 5 · THE 30-DAY CALENDAR, THEN WAIT

Write content-engine/<YYYY-MM>/calendar.md: one row per day, 30 days:

  Day · Platform(s) · Format (CAROUSEL / SINGLE POST / VIDEO) · Hook · Why it'll work (link to

  the finding) · CTA / comment keyword

Default mix (change it if I ask): ~12 carousels · ~10 single posts · ~8 short videos.

Every idea must pass the money test: does it make someone more likely to call, book, DM, or

trust me? Never reuse a comment keyword. Lead the month with the strongest hooks.

For every VIDEO day, write the full script with the niche-content-engine script rules (hook in

the first 3 seconds, 90–160 spoken words, one real detail from my trade, no brackets or

placeholders), plus a short "just the idea" version for when I'd rather talk freely.

Put them in content-engine/<YYYY-MM>/teleprompter.md, clean, ready to paste into a teleprompter.

Show me the calendar and STOP. I'll tell you what to change. Nothing gets built until I say go.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 6 · BUILD THE CAROUSELS AND POSTS

Use the carousel skill for every CAROUSEL day, and a 1-slide version in the same style for

every SINGLE POST day. My style sheet on every one: page one looks like page seven.

  • My own photos → own-photos mode. They stay on this machine, never uploaded.

  • No photos → style-sheet mode. Free ($0) by default. Paid (Higgsfield) only if I ask:

    tell me the total credit cost first and wait for my "go".

  • Text is always rendered by code, numbers are verified at the source, logos are real.

  • LOOK at every slide you export and fix anything broken before showing me.

Write a caption + hashtags for each one in my voice. Save everything to

content-engine/<YYYY-MM>/day-XX/ so each day's files are in one folder.

Show me a contact sheet of the whole month at the end.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 7 · EDIT MY VIDEOS (whenever I send one)

When I drop a raw recording and say which day it is, edit it with the persa-short-editing

skill: 9:16 1080×1920, cut the dead air, full display-type pass, and pull real screenshots and

screen recordings of whatever I talk about (if I say "look at this website", that website is

on screen). Follow the skill's order of work exactly: decode → transcribe → fact-check →

source → framing → build → gates → render → sound → deliver.

  • Before building, show me the list of media you plan to use for each beat, and wait for OK.

  • If the video has no product/website demo to carry the screen, tell me in one line and

    propose the closest edit instead of forcing it.

  • The sfx/ and bgm/ folders ship empty. If I haven't added sounds, ask once, or deliver

    without them and say so.

  • Watch sampled frames of the final render before you tell me it's done. Open it for me.

Save it to content-engine/<YYYY-MM>/day-XX/.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 8 · SCHEDULE EVERYTHING WITH BLOTATO

Once I've approved the finished pieces, use the Blotato connector to schedule every item on its

calendar day and platform, with its caption. Show me the full schedule (date · time ·

platform · file · first line of caption) and WAIT for my "schedule it" before you send

anything. Videos get scheduled as I send and approve them.

Afterwards, confirm what was scheduled and list anything that failed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULES

- Never spend credits, and never publish or schedule anything, without my explicit OK.

- Never invent facts, numbers, reviews, or customer stories. Stories come from me.

- No medical/legal claims, no attacking named competitors, no guaranteed outcomes.

- Keep me posted in short lines. Show me finished work, not your process.

- Next month, when I say "New month. 30 days.", read brand.md, skip setup, and start at

  STEP 4.

Start now with STEP 1.
```
