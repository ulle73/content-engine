# SOURCING — what to go and find on the web

Written 2026-08-10 from Jad's note:

> "when you go fetch things online from the context of the video — I don't need you to get only
> blogs and things like that, that's mad boring. I need more like Reddit posts, Twitter posts,
> videos of dashboards that make sense of what I'm talking about, or videos of the specific
> thing that I'm talking about. You get extra points if you find the thing I talk about and you
> find a video about it. But I don't want to see a person in the bottom corner screen-sharing
> and talking — it has to look completely as if I did the screen share."

Read this with [`BLACKLIST.md`](BLACKLIST.md) and the concept catalog (`CONCEPTS.html`). The
catalog says *what kind of thing* to show; this says *where to get it and how to judge it*.

---

## 0 · The one hard rule

**It must look like HE recorded it.**

No webcam bubble in the corner. No presenter's face. No "hey guys welcome back" framing, no
YouTube UI, no channel watermark, no subscribe overlay, no mouse-drawn annotations, no other
creator's captions burned in.

If a clip has a talking head in the corner, it is **unusable** — not croppable, not fixable.
Crop it out and the frame is off-centre and the layout is broken. Find another clip.

The one exception: the person **is** the subject of the line (the tool's creator on the record,
a named speaker being quoted). See BLACKLIST #5.

---

## 0a · SOURCING IS STEP ZERO — approved BEFORE a beat is built

**Added 2026-08-10. This is now the first thing that happens on every video.**

> "when I tell you going to the internet and find me those videos, I think that should be the
> FIRST thing that you should be doing. You need to understand what the video's about and where
> do you think you want to put the videos on the video, the real, BEFORE you edit. So I need you
> to open for me those three videos to see if those are the things that I want to look at, and I
> need a bit of context of 'oh this is for this part and this part and this part'. If I approve
> them you just do it, if I don't you keep looking for more."

The order is: **read the script → decide what real media it needs and WHERE → go find it →
open it for him → he approves → then edit.** Never discover media halfway through a build, and
never cut something in that he has not seen.

```bash
python scripts/source-scout.py work/nextphase/videos/<slug>/scout.json      # writes + opens SOURCING.html
python scripts/source-scout.py work/nextphase/videos/<slug>/scout.json --only c3   # re-scout one rejection
```

`scout.json` names, per candidate: the **beat** it is for, **where** in the video it lands, the
**line** it sits under, the **slot** (above his head / coral half / full frame) and **why that
clip**. The page plays each clip inline beside that context, with a contact sheet under it so
the disqualifiers are visible.

Then ask him — one question, multi-select, one option per candidate. **Yes → cut it in. No →
keep looking and scout again.** Do not argue a rejection; find another.

**Show it EARLY and rough, not late and perfect.** Added 2026-08-11 after he had to ask
mid-build: *"What happened to you showing first what you got from the internet"*. The candidates
had been found within minutes; the next hour went on shooting, cropping and fixing them before
anything reached him — and two of the assets he then redirected entirely. Open the page as soon
as you have one real option per beat. A rough page he can steer beats a polished one built on
the wrong premise, and everything after the redirect is work you do not have to redo.

Two things the scout does automatically because they have already cost a render:
- pulls at **>=1080p**. yt-dlp's default returned 640x360 and terminal text was unreadable once
  scaled into a 1000px slot.
- flags any clip under 1600px wide as likely illegible at 9:16.

It does **not** judge the webcam bubble, another creator's captions, or YouTube chrome — look at
the contact sheet. That judgement is the whole point of opening the page.

## 0b · WHEN to fetch, and WHERE it goes in the cut

**Fetch only for things the library does not already cover.**

| He says | Do |
|---|---|
| Claude Code, Claude, ChatGPT, Gemini, Grok, Perplexity, sessions, skills, permissions | **Do not fetch.** We have the real UI as a block — `CONCEPTS.html` |
| A tool we have never covered — Kimi, Hermes, a new model, a specific product | **Fetch.** This is exactly what sourcing is for |

### ⭐ OPEN THE LIBRARY BEFORE YOU OPEN A BROWSER — added 2026-08-11

The table above is not new, and it was still broken on `ai-seems`, a video that is Claude Code
end to end. Jad, twice:

> "no use the ui's that we have in our library man and show them to me"
> "why are you not using the ui of an actual claude code session???"

The rule was written down; what was missing was a STEP that makes you look. So:

```bash
python scripts/build-block-picker.py --all                     # the whole library, live
python scripts/build-block-picker.py work/nextphase/videos/<slug>/blocks.json # per beat, for approval
```

**Run this before `source-scout.py`, not after.** If the picker covers the video, there is
nothing to fetch and the web step is skipped entirely.

**⚠ IT WAS SKIPPED AGAIN ON tp-0817b, AND HERE IS WHAT THAT COST — 2026-08-18.**
Jad: *"I would love more UIs and animation — you can simply just look at the library."*
The picker was never run. No `blocks.json`, no `BLOCK-PICKER.html`, no page put in front of
him. Instead a handful of registry previews were spot-checked with ffmpeg, so the cut reached
for whatever had already been seen. Measured against what was on the shelf:

| pool | on the shelf | used |
|---|---|---|
| registry blocks + components | **356** | **2** |
| our own ui-blocks | 12 | 1 |
| mascots | 24 | 5 (and 0 until he asked twice) |
| real UI crops | 10 | 0 |

Two of three hundred and fifty-six. The library was not "consulted and found wanting" — it
was never opened. **Running the picker is not a formality that precedes the real work; it IS
how the assets get chosen.** If there is no `BLOCK-PICKER.html` or per-beat `blocks.json` for
a video, the library step did not happen, whatever the build header claims.

**Two more failures it exists to prevent, both real:**

1. **Fetching what we own.** An hour went into shooting docs pages for a video whose spine was
   four blocks we already had.
2. **Reaching for the ADJACENT block instead of the right one.** `sessions-grid` draws generic
   terminal cards. It is *not* the Claude Code UI, and it was rejected on those grounds. If he
   names a product, the asset has to be **recognisable as that product** — its banner, its mark,
   its chrome. `ui/claude-code-window.png` reads as Claude Code because it carries
   the `Claude Code v2.0.0` banner, the model, the cwd and a live prompt. A bare `›` prompt with
   a status bar does not: *"use a, c doesn't look like a claude session."*

**And when a block is nearly right, RETYPE IT — never fork it, never ship the wrong words.**
Blocks ship with the copy of the video they were built for. `skills-beat` typed `/skills`;
`claude-new-chat` typed an Instagram reel URL. Both now take parameters
(`?cmd=` `?menu=` `?prompt=`) so the next video changes the text instead of copying the file.
Only ever put **real** product copy in: invented UI text is a fabricated interface. `/statusline`'s
real help string is "Set up Claude Code's status line" — that was looked up, not written.

**Three times, spread across the cut** — beginning, middle, near the end:

1. **In the hook.** The sourced media sits **above his head in the Transparent layout**, so the
   first thing on screen is the real thing he is naming. This is the one that matters most.
2. **In the middle**, as a split or a b-roll-full beat.
3. **Near the end**, before the CTA.

A short with one sourced asset at 0:30 and nothing else feels like a talking head with a
slideshow. Three sightings, opening on one, is the shape.

## 1 · Priority order — best first

| | Source | Why it wins | How |
|---|---|---|---|
| 1 | **Real footage of the exact thing** | Nothing beats the actual feature moving. Extra points, his words. | `yt-dlp --download-sections`, then check for a webcam bubble |
| 2 | **A dashboard / console in motion** | Numbers moving on a real surface reads as proof | screen-record the real product, or find a demo clip |
| 3 | **A Reddit thread** | Real people reacting; the title alone often IS the hook | **real browser only** — see §2b |
| 4 | **An X / Twitter post** | Announcements, receipts, the founder saying it | **real browser only** — see §2b |
| 5 | **A repo / release page** | Concrete, dated, verifiable | `opengraph.githubassets.com/1/<owner>/<repo>` |
| 6 | **The official docs page** | Authoritative, but visually dead — use only for a claim | `scripts/shoot-page-9x16.py` |
| — | ~~A blog post~~ | **"mad boring."** Never the first choice, rarely the fifth. | |

**A designed block beats a bad source.** If the only real media is dull or unusable, build the
scene instead — that is what `ui-blocks/` is for.

---

## 2b · Reddit and X block headless browsers — verified 2026-08-10

Both return **HTTP 200 and render a perfectly valid screenshot of a bot wall**
("You've been blocked by network security"). `old.reddit.com` is blocked too. Nothing errors;
you just get a beautiful 1080×1920 picture of nothing, which is exactly how a blank panel ships.

`scripts/shoot-page-9x16.py` now **refuses** to write a shot whose page reads as a wall or has
under 220 characters of text. It saves `<name>.REJECTED.png` so you can see what came back, and
exits non-zero.

**The route that works:** drive the user's own logged-in browser (Claude in Chrome), navigate
there, and screenshot the post from the real session. Ask him to open the thread if it needs a
login. An official embed (`publish.twitter.com`, reddit's embed iframe) is the second option.
Never fake a Reddit or X post in your own styling — it is a fabricated record.

## 2 · Judge every clip before you commit

`scripts/fetch-source.py` downloads, normalises **and lays out a contact sheet**. Look at it.
Every rejection below has shipped in someone's edit:

- a **webcam bubble** bottom-right (the hard rule)
- another creator's **captions** burned in
- a **cursor trail** or click-highlight effect
- **YouTube chrome** — end cards, watch-later, a paused scrubber
- the clip is **16:9 with tiny UI** — at 9:16 it will be unreadable (BLACKLIST #1)
- it is **a slideshow of stock footage**, not the thing itself

## 3 · Rights, before it reaches a render

These are monetized, client-facing shorts. Flag anything you cannot answer:

- **Reddit / X**: quoting a public post as a screenshot is normal editorial practice; **lifting
  someone's video** is not. Prefer the post over the video.
- **YouTube**: a short excerpt used to comment on the thing is one thing; a long lift is another.
  Keep excerpts to ~4–6 seconds and make the point about the thing, not the video.
- **Anything with a person in it**: needs a reason to be there. See BLACKLIST #5.
- If rights are unclear, say so **before** it is cut in. Never quietly ship it.

---

## 4 · Recipes

```bash
# Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs

# a real clip of the thing — probe FOUR points before committing to one
python scripts/fetch-source.py video "<url>" assets/broll/thing.mp4 --probe

# then take the window you actually want, normalised to 30fps CFR
python scripts/fetch-source.py video "<url>" assets/broll/thing.mp4 --at 3:12 --dur 5

# a reddit thread as a 9:16 frame (post, not the video)
python scripts/fetch-source.py reddit "<permalink>" assets/broll/thread.png

# an X post as a 9:16 frame
python scripts/fetch-source.py x "<status url>" assets/broll/post.png

# a repo card — 44 kB, instant, always current
curl -o assets/broll/repo.png "https://opengraph.githubassets.com/1/<owner>/<repo>"
```

**Every sourced clip is normalised to 30fps CFR.** `yt-dlp` returns 24/25/50/60/VFR, and dropped
into a 30fps composition it judders or drifts off the beat it was cut to. `fetch-source.py` does
this for you; verify with `ffprobe -show_entries stream=r_frame_rate,avg_frame_rate`.

**Every sourced page is shot 9:16 at a narrow viewport** — `scripts/shoot-page-9x16.py`, never a
crop of a desktop page. See BLACKLIST #1 and #3b.

---

## 5 · Where it goes

Sourced media lands in `work/nextphase/videos/<slug>/assets/broll/`. Anything reusable across videos gets
promoted to `pages/` (page shots) or `broll-library/clips/` (footage), and added
to `library/concepts.json` so the next edit finds it instead of re-sourcing it.
