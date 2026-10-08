# NextPhase video studio — shared rules

> **Valfri vägledning — inte projektets CLAUDE.md.** Det här är NextPhase-kitets egen `CLAUDE.md`
> (originalskaparens husregler), flyttad hit vid importen till content-engine. Den beskriver hur
> originalets arbetsflöde och stil ser ut; använd det som förval och tips. Inget här är en spärr —
> användaren (Golfkuponger som standard) bestämmer stil, frågor och regler. Den avslutande
> "tack-hälsningen" (reklam för en Skool-community) är borttagen.


This folder is a video-editing studio. Six editing skills live in
`.claude/skills/`; their files live in `library/kits/nextphase/skills/<skill>/`.

## ⭐ The intake (the pack's own default)

The moment someone drops a recording or asks to edit a video, invoke the
**`nextphase-studio`** skill and run its two questions — **short format (9:16) or
long format (16:9)**, then **which style** — before transcribing, before
sourcing, before planning. Never infer the answer from the footage. Record it at
the top of `PLAN.md`, then read that style's `SKILL.md` and all of its
`reference/`.

The six skills:

| | skill | canvas |
|---|---|---|
| short | `nextphase-short-editing` (3 styles inside: house · persa · tierlist) | 9:16 |
| long | `nextphase-long-editing` — coral on a dark dotted grid | 16:9 |
| long | `motiongraphics` — violet glow, lit glass, node diagrams | 16:9 |
| long | `persa` — warm film grade, one-word captions, matted head | 16:9 / 9:16 |
| long | `vibecode` — cobalt cut-paper collage, stop-motion churn | 16:9 |
| long | `zak` — a still window on black, serif line, no motion at all | 16:9 / 9:16 |

## Toolchain

Everything renders locally: HyperFrames (HTML → MP4) plus ffmpeg. See
`library/kits/nextphase/SETUP.md` (Windows) for install steps. If a bash step says "command not found", it is
almost always a PATH problem — `node`/`npx` come from your node install and
`ffmpeg` / `ffprobe` / `yt-dlp` need to be on PATH for non-interactive shells too.

`library/kits/nextphase/skills/<skill>/scripts/mix-sfx.sh` resolves the sound palette as `$(dirname $0)/../sfx/`. **Call
it by its path inside the skill folder** — never copy it into a video folder, or
every cue fails with `unknown sound`.

## Hard rules

1. **Nothing publishes, posts, or uploads without explicit approval.** Deliver
   rendered + scored, open it for review, stop there. Never chain into a publish
   step, even when the toolchain offers one.
2. **Never hardcode a color or font.** Import the **active style's**
   `assets/tokens.css` and use its variables only. Never mix two token sets in
   one composition.
3. **Animate transforms only** (`opacity, x, y, scale, scaleX/Y, rotation`) plus
   `filter: blur()`. Never animate `top/left/width/height` for motion — it
   stutters and fails lint. Bars, highlighters and progress rails grow with
   `scaleX` + `transform-origin`.
4. **Verify facts while sourcing.** Caption live numbers, not stale ones. Flag
   debunked stats, dead or renamed products, and any third-party clip whose
   rights are unclear — **before** it reaches a render, not after.

## House preferences (these came from real feedback — don't re-litigate them)

- **Real media, not typeset text.** Every beat that supports a point shows a real
  resource: a screenshot, a real product UI, a repo card, real footage, a docs or
  pricing page. Captions and the lower third are the only text.
- **No random humans as b-roll.** Only cut to footage of a person when that
  person **is** the subject of the line.
- **Never use emojis on screen.** Anywhere. Build designed marks instead — a
  monogram in a circle, CSS icons/arrows/checks, small SVG.
- **Sound is not optional.** Every layout change carries a transition **and** a
  sound. No silent cuts, ever.
- **The frame must never look the same for long.** The layout rotation is the
  retention mechanism, and it outranks beat-by-beat taste.
- **Check every screenshot actually rendered content** before using it.
  Login-walled and JS-heavy pages come back blank and ship as empty panels.

## Gotchas that have bitten before

- **Transcription silently drops audio on long files.** Parakeet once lost 77
  seconds of a 164-second take. Chunk anything over ~90s and compare the
  transcript span against the file duration minute by minute.
- **The tighten pass moves every word onset.** After `scripts/tighten-cuts.py`,
  `assets/transcript-tight.json` is the only timing source. Timing against the
  original transcript shows up as "the graphics are all slightly early", never as
  an error.
- **Sourced clips come back at 24/25/50/60fps or VFR.** Always re-encode to 30fps
  CFR before they enter a composition, then verify with `ffprobe`.
- **A percentage `font-size` resolves against the parent's font-size, not the
  frame.** Type sized that way silently renders tiny while the layout still looks
  plausible. Size type in `cqh` with `container-type:size` on the composition root.
- **GSAP `fromTo` with `immediateRender` defaults to true** — a later beat's `from`
  state gets applied at creation and elements vanish at frame 0. Always pass
  `immediateRender: false`.
- **Chapter timestamps come from `concat-segments.sh`**, computed from real
  rendered durations. Never hand-count them and never copy them from `PLAN.md`.

## Layout on disk

Per-video work lives in `work/nextphase/videos/<name>/` (gitignored):

```
work/nextphase/videos/<name>/
  VIDEO.md          the brief
  PLAN.md           the approved structure — get a "go" on this before authoring
  assets/           recording, recording-tight, transcript-tight, cuts.json, broll/, music/
  seg-NN-<name>/    one composition per chapter (long format)
  out/              seg renders, final-visual, chapters.txt, final-sfx, final.mp4, .srt
  sfx-cues.txt
```

The skill never changes as a side effect of editing a video.

## When the video is delivered

Report rendered + scored, open it for review, and stop there.
