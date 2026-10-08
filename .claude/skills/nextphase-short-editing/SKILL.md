---
name: nextphase-short-editing
description: >-
  NextPhase SHORT (9:16) – redigera en talking-head-short med HyperFrames-grafik ovanpå kameran: hook → face → body → CTA, ordsynkade grafiker, riktig källmedia, gul highlighter-teknik, logga-blur-reveal, pop-out-matte (RVM), ordvisa captions (Parallax / Weight Shift / Highlighted), tier board och tät SFX-pass. Tre stilar: house (cream-platta), persa (full bleed), tierlist. Använd när användaren väljer en NextPhase short-stil eller vill ha dessa tekniker.
---

# NextPhase — SHORT editing skill (9:16)

> **Importerad till content-engine — kit `nextphase` (NextPhase Skill Pack).**
> **Varumärke:** Standardlooken är Claude-tema (coral `--coral` på cream, Claude-UI-block, AI-exempel i `library/concepts.json`). Teknikerna är det värdefulla — copy, loggor och färger är utbytbara (färgerna sitter i `assets/tokens.css`). Biblioteksanvändaren är som standard **Golfkuponger** (svensk golf, svensk text; se `skills/golfkuponger-brand/`) — byt gärna till dess färger och ton, men inget här är en spärr. Kitets "hard rules" och husregler beskriver hur originalstilen ser ut; se dem som förval och tips, inte krav. "Jad/han" i texten = originalskaparen, för oss = användaren.
> **Sökvägar:** kitfilerna ligger i `library/kits/nextphase/skills/nextphase-short-editing/` — `reference/…`, `components/…`, `scripts/…`, `assets/tokens.css` m.m. nedan betyder den mappen (`SK=library/kits/nextphase/skills/nextphase-short-editing`). Per-video-filer (`assets/recording.mp4`, `out/…`, `PLAN.md`, `seg-NN/`, `sfx-cues.txt`) ligger i `work/nextphase/videos/<namn>/` (gitignorerat). Kör skript med full sökväg från repo-roten, t.ex. `bash library/kits/nextphase/skills/nextphase-short-editing/scripts/<skript>.sh …` / `python library/kits/nextphase/skills/nextphase-short-editing/scripts/<skript>.py …`; videofilerna i kommandona (`out/…`, `assets/…`) är då `work/nextphase/videos/<namn>/out/…` osv.
> **Windows:** Git Bash för `.sh`, `python` (aldrig `python3` — det är Store-stubben), Chrome i `C:\Program Files\Google\Chrome\Application\chrome.exe`, RVM-venv i `library/.venv` (signerad Python 3.12). Installation: `library/kits/nextphase/SETUP.md`.
> **Ljud (gratis som standard):** `python library/kits/nextphase/skills/nextphase-long-editing/scripts/make-free-sfx.py` (resp. `nextphase-short-editing/…`) fyller `sfx/` från HyperFrames SFX-bibliotek (Pixabay) + syntes. `scripts/gen-sfx.sh` (ElevenLabs) är betald och valfri. Originalets betalda SFX-pack, musikbädd, maskot, loggor och referensstills togs bort — se `library/kits/nextphase/IMPORT-NOTES.md`.
> **Husregler:** kitets `CLAUDE.md` finns som valfri vägledning i `library/kits/nextphase/reference/nextphase-house-rules.md`.


You are the motion-graphics editor for a monetized AI-news / how-to SHORT. You edit **one** video at a time: a talking-head recording goes in a bottom camera card, and you overlay HyperFrames graphics in the top zone, with big karaoke captions throughout. The default look is the **cream** house style — but there are **three** styles now and you ask which one first (step 0). Everything below is the bar — an edit that misses timing, media, **or** sound is not done.


> ## ⭐ READ THESE SEVEN FIRST, IN THIS ORDER
> 0. `reference/STYLES.md` — **THERE ARE THREE STYLES NOW.** Pick one before you do anything
>    else, including transcribing. `house` (the cream plate) is the default and is what you
>    use unless Jad names another. `persa` (full bleed) is the second preset — "the other
>    style", "the Instagram style", "the full-bleed one", persa. `tierlist` (a tier board
>    owning the top half) is the third, added 2026-08-27 — "the tier list one", "the ranking
>    one", tierlist. Four BLACKLIST rules are HOUSE-ONLY: persa suspends #2b, #7, #11, #12;
>    tierlist suspends #2b (for the card only), #7 and #11 but keeps **#12 in force**.
>    **Two of the three have a PRECONDITION that can veto his choice** — persa needs a real
>    15s+ demo, tierlist needs a transcript that actually ranks 4+ named things. Say so
>    before you build, not after.
> 1. `reference/BLACKLIST.md` — what never goes in a short. Check a cut against it BEFORE rendering.
> 2. `reference/HOW-WE-EDIT.md` — the operative handoff.
> 3. `library/concepts.json` — what to SHOW for what he SAYS. The rule that governs it: a product
>    is shown as its real UI, animated; a mascot is only ever the actor tending it, never the
>    thing itself.
> 4. `reference/SOURCING.md` — before fetching anything from the web.
> 5. `reference/TYPE-ROLES.md` — the FOUR display-type roles (title stack · the
>    hollow-outline "gradient" word · the coral payoff · the lime in-UI annotation),
>    torn down from the reference reels. They run ALONGSIDE the three caption styles,
>    they never replace one, and they only work on a photographic ground. **persa only.**
> 6. `reference/TIER-BOARD.md` — the tier board's measured geometry, the PRESENT-then-PLACE
>    move, the re-rank, and why this is the one style with no matte. **tierlist only.**
>    Build it by COPYING `components/tier-board.html` — never by re-typing it.
>
> `HOW-WE-EDIT.md` carries the HyperFrames clip contract (the bug that silently puts every
> element on screen for the whole video), the camera geometry, why blocks must be rendered to
> **video** and never used as stills, how assets are chosen by **meaning**, the caption band, the
> old CTA, the density gate and the fixed sound cues. Everything in it was learned by shipping
> something broken.

## 📦 Tredjepartsmaterial
Originalets `bgm/`, `sfx/`-ljud, `clawd/` (maskot), `brand/` (loggor), `pages/`, `ui/` och
`src-demo/` var andras material och togs bort vid importen; neutrala platshållare + README ligger
på samma platser (`brand/`, `mascot/`, `ui/`, `pages/example-page.png`). `WHATS-INCLUDED.md`
beskriver originalets uppdelning. `python library/kits/nextphase/skills/nextphase-short-editing/scripts/verify-package.py`
kontrollerar att refererade sökvägar finns.

## ⛔ THE ORDER OF WORK — do not reorder these
```
 0 STYLE       ⛔ ASK HIM. EVERY TIME. Before transcribing, before anything:

                   "Which style — A (house, the cream plate), B (persa, full bleed),
                    or C (tierlist, the board)?"

               Do NOT infer it from the recording and do NOT default silently. He asked for
               this explicitly on 2026-08-27: "sometimes whenever I give you a video, you're
               like, which version do you want it? A or B? And I choose, and then you do it
               on that style."
               The only time you skip the question is when he names the style himself in the
               same message he drops the recording. Read reference/STYLES.md before building:
               the plate, the caption bands, whether display type exists, whether a matte is
               needed at all and which BLACKLIST rules are in force all differ.
               THEN CHECK THE PRECONDITION before you build — B needs a real 15s+ demo,
               C needs a transcript that ranks 4+ named things. If his pick fails its
               precondition, say so in one line and recommend A.
0  LIBRARY FIRST     (build-shelf.py kräver en lokal registry-förhandsvisningsmapp som inte följer
                     med — använd `npx hyperframes catalog` / skillen hyperframes-registry)
                     scripts/build-shelf.py -> READ ALL FIVE SHEETS (199 usable registry
                     animations, 42 to a screen, named). THEN build-block-picker.py for our
                     own blocks. Only what the library does NOT cover goes to step 1.
                     Skipping this is why tp-0817b used 2 of 356 registry items.
1  SOURCE FIRST      find the real media, and get it APPROVED, before building anything
2  STORYBOARD        show the beat map with real frames — before rendering
3  BUILD             author index.html against the clip contract
4  GATES             hyperframes check · check-density.py · BLACKLIST.md
5  RENDER            then SAMPLE THE RENDERED MP4, never a snapshot
6  SOUND             a separate pass on the locked render, gains MEASURED
7  BED               lay-bed.sh, then open for review. Publish nothing.
```

**⛔ Two hard rules**
1. **Never hardcode a color or font.** Import `assets/tokens.css` into every scene; use its CSS variables only.
2. **Animate transforms only** (`opacity, x, y, scale, scaleX/Y, rotation`). Never animate `top/left/width/height/borderWidth` for motion — it stutters and fails lint (`gsap_non_transform_motion`). Bars/highlighters grow with `scaleX` (+ `transform-origin`), never `width`.

Read `reference/` in full before building: `edit-standard.md` (the mandatory bar), `design-system.md` (look), `motion-grammar.md` (how things move), `editing-rules.md` (timing + safe zones), `sound-design.md` (the SFX pass), `cutout-compositing.md` (background removal + the pop-out hook), `logo-reveal.md` (the blurred-logo name reveal).

---

## 0 · The frame (safe zones — never violate)
- **Canvas:** 1080×1920, 30fps.
- **TOP zone `0–800px`** = graphics live here (the upper ~42%).
- **CAPTION band `820–940px`** = karaoke captions (drop to `y+646` during full-screen beats).
- **CAMERA card `960–1920px`** = the talking head (~50% of frame). Reserved — never cover it except during a deliberate full-screen beat.
- **Full-screen beats** (face or b-roll takeover) use a second full-frame layer above the card; captions ride on top and keep running.

## 1 · The ARC — every short follows this anatomy
1. **Hook** (0 → end of hook line): camera in the bottom card, **web media + animation from second one** (never a lone static title, and never a small dark screenshot with a highlighter on it — unreadable at reel scale), a **`riser` building** underneath.
   - ⭐ **When the reel withholds a product name, the hook is the LOGO BLUR-REVEAL** (`reference/logo-reveal.md`, brick: `components/logo-blur-reveal.html`): the tool's **real** logo sits blurred from second one and the blur resolves **on the transcript onset of the name**. That reveal IS the payoff beat — it takes the coral flash and the `magic-reveal`.
2. **Hook payoff** (on the punch word): a **reveal (scale/blur-in) + a coral flash cut**, the riser crests. ← fixed signature.
3. **Full-screen FACE hold (~2s)** immediately after the hook: the camera scales to fill the ENTIRE frame, top graphics clear, **captions keep running**, with a **Slow Push** zoom. A breath / eye-contact beat.
4. **Body**: camera back to the bottom card; word-synced top-zone graphics + ≥4 real media + dense sound. Push-transition every top-zone swap.
5. **Mid full-screen B-ROLL takeover (~3–8s)**: ONE designed HyperFrames graphic (or a real article-highlight page) fills the frame, captions stay — the "explainer" beat.
6. **1–2 extra full-screen FACE beats (~2s)** on emphatic/"here's the catch" lines — use **Face Punch** or **Handheld Drift**.
7. **CTA** close: `Comment "KEYWORD"` pill + CSS arrow.

### ⭐ THE ROTATION — a change of CAMERA TREATMENT, not of graphic
The single most-rejected mistake. Swapping the picture inside the same treatment is **not** a
change: transparent-with-media and b-roll-on-cream are the SAME frame, so 14 seconds of them
reads as one screen. There are four genuinely different frames:

| frame | what the camera is doing |
|---|---|
| **TRANSPARENT** | the composited pop-out on cream, media ABOVE his head (`base.mp4`, full frame) |
| **FULL FACE** | the raw take filling the whole frame (`recording.mp4`) |
| **SPLIT SCREEN** | media owns the top half, the camera card the bottom |
| **B-ROLL FULL** | media owns the whole frame, **no camera clip at all** |

- **Never two neighbours alike. Never hold one past ~8s.**
- The arc: hook on TRANSPARENT → his FULL FACE → SPLIT → keep rotating.
- **Every layout change carries a transition AND a sound.** No silent cuts, ever.
- **Rotate the transition sound too** — the same `swell` on all fourteen reads as a tic. Keep
  `swell` for the structural beats and alternate `swoosh` / `whoosh-2` between them.
- Assert it in the build so it cannot drift:
```python
for i in range(1, len(BEATS)):
    assert BEATS[i][2] != BEATS[i-1][2], "two neighbours share a camera treatment"
```

### ⭐ REAL MEDIA, NOT TEXT — every supporting beat
Typeset text graphics are banned as support. Every beat that backs a point shows a **real resource**: a screenshot, a real product UI, a repo card, real footage. Captions are the only text; the CTA pill is the one exception.
- When he names a tool, show **that tool's real UI**. Render the remocn `claude-chat` / `chat-gpt` / `claude-code` components with his actual text (Remotion → MP4), **crop tight to the composer bar** — the full 1280×720 frame is unreadable at reel scale — then drop the MP4 in as a root `<video>`.
- **Half & Half: the ANIMATION HALF ITSELF is a `--coral` block**, full bleed, edge to edge — so the split reads instantly as a split. The media sits inside it with a **thin** margin (~40px). Do NOT put a coral frame around the media and call it done; the *half* is what gets highlighted, not the picture.
- **Check every screenshot actually rendered content.** Login-walled/JS pages come back blank and ship as empty panels.

### CAPTIONS — three styles, one word at a time
**Word by word, always.** One word on screen; it pops in on its own transcript onset, drops out, the next pops up. Never a chunk of words with a moving marker.

| Style | Look | Use it for |
|---|---|---|
| **Parallax** | Instrument Serif, `--red`, big, enters with a vertical stretch (`scaleY 2.8 → 1`) | the lines that matter — hook, hero moment, close |
| **Weight Shift** | Montserrat, weight 300 crossfading into 900 as the word lands, `scale .85 → 1` | normal narration |
| **Highlighted** | white on a `--coral` marker that sweeps in behind the word | every Half & Half beat, matching the coral half |

There are **three** styles. A fourth, **Chrome** (silver gradient), was deleted 2026-08-20 —
*"I never want to see it ever again."* Face beats take **Parallax at y1400**.

Assign styles **per beat** — "important" is a directorial call, not something in the transcript.

**Position — by layout:**
- **Half & Half (either direction) → THE SEAM**, `y960`, centred on itself. The middle of the screen, where the halves meet: never on his face, never buried in the media. *(Tried and rejected: middle of the animation half — it lands on the media; bottom of frame — he didn't want it.)*
- **Transparent → chest**, `~y1500`. Below the chin, above the card.
- **B-Roll → clear of the media**, `~y1480`.
- **Face → chest**, `~y1450`.

**Drop captions entirely when the picture already says it** — a beat showing him typing a prompt in a real UI, or the CTA. Redundant captions there read as clutter.

**Never put captions behind the cutout.** Behind-subject parallax was tried; at chest height his body occludes the word completely.

### CAPTIONS — style follows the layout
- **Half & Half (both directions) → HIGHLIGHTED.** Active word on a `--coral` marker block, `--cream` text, 14px radius. The Claude highlight look. Animation Up → band `820–940`; Face Up → band moves to the seam `~985`.
- **Transparent Background → default** (`--ink`, no highlight), riding **high above the head** (~`y300`) on a soft scrim so it never crosses the face.
- **B-Roll → default**, sitting **BELOW the media** (~`y1420` for a letterboxed 16:9). **Captions must never overlay the b-roll.** Full-bleed page → drop low on a scrim.

### TRANSPARENT BACKGROUND — he moves DOWN, media goes above his head
Media must never overlap his head. Do **not** shrink the media to fit — slide **him** down instead:
- `tl.set("#cut",{y:TRANS_SHIFT})` **and** `tl.set("#camrect",{y:TRANS_SHIFT})` — *both, by the same amount.* Moving one without the other breaks the seam and ghosts a second pair of shoulders.
- `TRANS_SHIFT ≈ 220`. The media zone is then `0 → HEAD_TOP + TRANS_SHIFT − 40`, where **HEAD_TOP is measured** by `scripts/find-cut-line.py`, never guessed. It recalculates per recording.

### TRANSPARENT BACKGROUND — layout (see `reference/cutout-compositing.md`)
The face is **cut out of its background (RVM)** and composited over the designed cream BG, torso showing through a rounded-rect window so he **pops out of the rectangle**. The house cut line is **MID-HEAD**. This is a LAYOUT, not a slot — it is the default opener (replacing hook + payoff) but is usable anywhere. The ~2s full-screen face hold and everything after are unchanged; the bottom camera card returns for the body.
- `scripts/rvm-matte.py` → BGRA frames · `scripts/cutout-hook.sh` → composite + audio.
- **Seam invariant: `RECT_Y − CROP_Y == PERSON_Y`.** The window torso and the cutout are the same body drawn twice; mismatch = a ghosted second pair of shoulders. The script hard-fails rather than ship it.
- Safe zones are suspended while this layout is on screen (the person *is* the frame); captions still run, clear of the head. Lanes resume the instant it ends.
- BG is a HyperFrames comp on **tokens** (`--cream`) — never the inherited white.

### Full-screen face ZOOMS (only when the face is full-screen — never on the bottom card)
- **Slow Push** (default, post-hook): origin `50% 46%`, scale `1.00→1.10`, `ease:"none"`.
- **Face Punch** (intimate/warning): origin `50% 38%`, scale `1.00→1.20`, `ease:"power2.inOut"`.
- **Handheld Drift** (cinematic line): scale `1.06→1.11` + small sine x/y sway.
Zoom the full-frame camera element only; captions do **not** zoom.

### PUSH transition on top-zone swaps
Outgoing slides out-left (`x:0→-540`, fade); incoming slides in from the right (`x:540→0`, fade, `power3.out`, ~0.44s). Top-zone graphics only — never the caption band or camera. Staggered lists push rows in one by one.

## 2 · Timing — RETENTION FIRST
- **No dead air, ever.** Nothing static holds >~4s: keep swapping graphics, give screenshots a slow zoom, stats a **count-up**, lists a stagger.
- **Anchor every graphic to the transcript word onset** — it enters ON (or a hair after) the exact word it illustrates, never before. Pull real times from `transcript.json`; round-number timings are banned.
- When a tool/company/site is named, show **that real thing on the word**. Exit at the OUT word +0.3s. ≤6s per graphic (the hero prompt/article card may run longer if it animates continuously). One idea on screen at a time.
- **Captions:** karaoke, ~3 words/chunk, `font-heavy` uppercase, word-synced. Fix ASR errors (brand names, the CTA keyword, number slips) while keeping sync.
- **Gap-check before editing:** Parakeet silently drops audio. Verify transcript span vs file duration; re-transcribe any >0.7s gap window and merge.

## 3 · Media — two layers, both required
1. **Real web-sourced media — ALWAYS, as inline cards (never the full-screen takeover):** **≥4 real per short.** Repo/OG cards, real screenshots, phone/browser-framed clips, tweets, pricing pages, articles. Prefer real **video** > images > text cards. Credit on-card. Tight crops only.
2. **The full-screen B-ROLL takeover = a DESIGNED HyperFrames graphic** (animated code/prompt panel, diagram, pipeline, compare) — never a raw web clip.
- **NEVER use emojis** anywhere on screen. Build designed marks (coral-circle monograms, CSS icons/arrows/checks/X). Emojis read as amateur.
- **Match platform to word:** "TikTok" → a real TikTok (phone-framed); "on GitHub" → the repo OG card; a stat → its source page.
- **ARTICLE-HIGHLIGHT** (`components/article-highlight.html`): when a real headline/stat/quote/claim is referenced, **screenshot the REAL article body**, show it filling 9:16 like a white browser page (slim chrome bar + real URL), then sweep a **yellow highlighter (`mix-blend-mode:multiply`, `scaleX` from the word onset)** across the actual words. Real screenshot + real words only — never re-typeset or invent. Captions drop low.
- **Verify facts while sourcing.** Caption live numbers, not stale ones. Flag debunked stats, dead products, or clips whose rights are unclear — never amplify a myth on screen.

### How to source (browser MCP is flaky — use these)
- `curl` GitHub OG cards: `opengraph.githubassets.com/<anything>/<owner>/<repo>` · READMEs via `raw.githubusercontent.com` · og:images.
- **Chrome headless** for site screenshots (run backgrounded with a kill-after-25s safety):
  `"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --window-size=1200,1500 --virtual-time-budget=9000 --screenshot=out.png "URL"`
  Many sites throw a cookie/consent modal that dims the page — crop above it, or brighten the crop with `ffmpeg -vf "eq=brightness=0.30:contrast=1.35"`. Cloudflare bot walls → pick another source.
- `yt-dlp` for real X / TikTok / YouTube clips (`--download-sections`), trim to ~4–6s.
- **⭐ NORMALISE EVERY SOURCED CLIP TO 30fps CFR.** `yt-dlp --download-sections` and GIF→MP4
  conversions come back at 24/25/50/60fps or variable frame rate; dropped into a 30fps
  composition they judder or drift out of sync with the beat they were cut to. Always
  re-encode: `ffmpeg -i in.mp4 -r 30 -fps_mode cfr -an -c:v libx264 -crf 21 out.mp4`, then
  verify with `ffprobe -show_entries stream=r_frame_rate,avg_frame_rate,nb_frames`.
- Crop tight with `ffmpeg -vf "crop=W:H:X:Y"`. Downscale huge PNGs with `ffmpeg -i in.png -vf "scale=1080:-2" out.png` (eller Pillow). Give any image reused across two beats its own copy (dodges the duplicate-media lint).
- **Windows-skärmdumpar:** Win+Shift+S lägger bilden i urklipp; be användaren spara den (t.ex. `Bilder\Skärmbilder\…png`) och ge sökvägen, eller använd den inklistrade filen direkt. Kopiera filer med glob om namnet innehåller specialtecken.

## 4 · Sound — a SEPARATE pass on the locked render (dense & varied)
- **⭐ HOOK payoff = `riser`, ALWAYS** — start it ~1.5s before the reveal so it crests on the payoff. The fixed signature.
- **Dense:** ~25–40 cues per short; nearly every move earns a sound. Silence is a deliberate breath.
- ⭐ **FIXED CUES (always, every video):** `swell` at 0:00 **and on every layout transition** · `riser` into the hook · `camera-shutter` on **each spoken part** of a platform name (OpenAI → 2 hits: "Open", "AI"; GitHub → "Git", "Hub") · bed = en egen rättighetsklar loop (originalets kommersiella låt är borttagen — se `bgm/README.md`). **All of it DIM** — punctuation, never announcement.
- **Varied palette — match the sound to the element** (don't lean on three): `whoosh`=zoom/in · `swoosh`/`whoosh-2`=out/air · `pop`/`click`/`futuristic-click`=appears · `confirm`=✓/land · `beep`=count tick/countdown · `magic-reveal`=hero reveal/highlight · `swell`=**every layout transition** (cut from Jad's own track) · `camera-shutter`=real media cut-in · `keyboard`=code/typing · `highlighter`=the article-highlight sweep · `ping`=CTA keyword.
- **Calibrate to the VO** (`ffmpeg -af volumedetect`): SFX sit ~13–15 dB under voice peaks. Hot VO → ~0.11–0.12 transients; quiet VO → ~0.07–0.09. Mix, then gut-check levels (SFX present but under the voice, no clipping).

---

## The workflow (every short)
0. **Locate the video folder.** Place the recording at `assets/recording.mp4`.
1. **Transcribe** → `assets/transcript.json` (word-level:
   `npx --yes hyperframes transcribe assets/recording.mp4 -e parakeet -o assets/transcript.json`).
   Gap-check against the file duration.
2. **⭐ SOURCE FIRST — before any editing.** Read the script, decide what real media it needs and
   **where each piece goes**, then find it and open it for approval. Four options per beat, one
   per source, each labelled with where it came from:
   ```bash
   python library/kits/nextphase/skills/nextphase-short-editing/scripts/source-scout.py work/nextphase/videos/<slug>/scout.json        # writes + opens SOURCING.html
   python library/kits/nextphase/skills/nextphase-short-editing/scripts/source-scout.py work/nextphase/videos/<slug>/scout.json --only b2   # re-scout a rejection
   ```
   Ask yes/no per beat. Rejected → find new options. Approved → build. Never cut in media he has
   not seen. Full doctrine in `reference/SOURCING.md` §0a.
3. **Matte the camera ONCE** for the whole video (`reference/cutout-compositing.md`) and
   composite one pop-out. Three separately-matted spans give three different framings and he will
   call it broken. Then **measure** where the base track carries raw footage — a TRANSPARENT beat
   that strays into a raw span flips framing mid-beat.
4. **Author `index.html`** — the arc above, tokens only, transforms only, word-synced captions.
   Every timed element carries `class="clip"` + `data-start` + `data-duration` +
   `data-track-index`, and **every concurrent element owns its own track**.
5. **Storyboard, before rendering:** `python library/kits/nextphase/skills/nextphase-short-editing/scripts/build-storyboard.py work/nextphase/videos/<slug>` — real
   frames, the arc role, the line, caption style, sound cues. Show him this.
6. **Gates:** `npx --yes hyperframes check .` (0 errors) → `python library/kits/nextphase/skills/nextphase-short-editing/scripts/check-density.py
   work/nextphase/videos/<slug>` → walk `reference/BLACKLIST.md` → then render.
7. **Render**, then **sample the rendered mp4**. The preview path and the render path disagree;
   a snapshot is not evidence.
8. **Sound pass on the locked render.** Write `sfx-cues.txt`, mix, then **measure every cue** as
   a delta against the visual-only render. Do not trust the gains.
   ```bash
   bash library/kits/nextphase/skills/nextphase-short-editing/scripts/mix-sfx.sh out/<slug>-visual.mp4 out/<slug>-sfx.mp4 sfx-cues.txt
   ```
9. **Bed:** `bash library/kits/nextphase/skills/nextphase-short-editing/scripts/lay-bed.sh out/<slug>-sfx.mp4 out/<slug>-FINAL.mp4` — a 36s loop that
   tiles to any length.
10. **Done:** report rendered + scored, open it for review. **Publish nothing** without explicit
    approval.

## The EDIT LIBRARY — open this before choosing anything
*(Följer inte med i kitet — använd `library/gallery.html`, `BLOCK-PICKER.html` och
`npx hyperframes catalog`.)* `catalog/index.html` (repo root) was the browsable inventory of every move available: the arc
slots in order, then the 88 remocn components for the b-roll takeover slot, then the 14 sound
cues (playable in the page). Each remocn card carries a **measured** 9:16 fit tag —
`9:16 safe` crops straight to vertical, `needs reframing` must be letterboxed, `landscape only`
never crops. Rebuild with `python catalog/build-catalog.py`.

## Files in this skill
```
reference/          the standards — read all of these before building
  BLACKLIST.md        what never goes in a short + the pre-render check
  HOW-WE-EDIT.md      the operative handoff (clip contract, camera, captions, density, sound)
  SOURCING.md         where to fetch from, in what order, and §0a: source FIRST
  sound-design.md     the palette, per-sound gains, leading silence, the bed
  cutout-compositing.md · design-system.md · motion-grammar.md · editing-rules.md ·
  edit-standard.md · logo-reveal.md
library/concepts.json  what to SHOW for what he SAYS — 14 concepts, trigger words, Show / Never
ui-blocks/          the live blocks. Every one animates and accepts ?seek=<s> — render them to
                    mp4, never screenshot them
  sessions-grid.html    babysit · parallel · approve · relay · machines
                        fits: full · half (1000x880) · head (1000x420)
  inbound-policy.html   the real accept / hold / refuse control
  page-highlight.html   a real page as a 9:16 frame + the marker. ONE mark at a time
  ai-new-chat · skills-beat · skill-folder · sessions-hub · claude-new-chat
scripts/
  build-block-picker.py ⭐ STEP ZERO — every library block, LIVE, for him to pick from. Run this
                        BEFORE a browser: if the picker covers the video there is nothing to
                        fetch. `--all`, or a per-beat blocks.json. An ADJACENT block is not the
                        right block — sessions-grid is generic terminals, not Claude Code
  source-scout.py     ⭐ STEP ONE — four candidates per beat, one per source, opened for approval
  build-storyboard.py the beat-by-beat page to show BEFORE rendering
  block-render.py     block -> mp4 (--bg renders onto the coral half)
  shoot-page-9x16.py  a real page as a true 9:16 frame, phrases located from the live DOM
  fetch-source.py     video/reddit/x, 30fps CFR, writes a contact sheet so you LOOK
  check-density.py    the gap gate — warn >4s, fail >6s
  mix-sfx.sh          mixes sfx-cues.txt onto a render
  lay-bed.sh          lays the 36s bed loop, tiling to any video length
  rvm-matte.py · cutout-hook.sh · find-cut-line.py · make-rect-mask.py   the pop-out
  build-concept-catalog.py · build-blocks-page.py · gen-sfx.sh
assets/tokens.css   the design tokens. Import into EVERY composition.
sfx/                the sound palette (gratis: scripts/make-free-sfx.py)
bgm/                (tom — lägg en egen 36s-loop, -34 LUFS, se bgm/README.md)
```

**PATH:** på Windows/Git Bash finns node, npx, ffmpeg och python redan på PATH — ingen export behövs.

## ⚠ The five that actually get cuts rejected
1. **The rotation is a change of CAMERA TREATMENT, not of graphic.** Four frames, never two
   neighbours alike, never held past ~8s.
2. **A product is shown as its REAL UI, animated.** A mascot is only the actor — never the
   session, the model, the app or the file.
3. **No small text, ever.** No docs-page crops, no headline cards, no tables of body type. If the
   only way to make the point is a wall of text, it belongs in the VO and the caption.
4. **Media sits IN the page.** No card behind it, no border, no rounded plate, no drop shadow —
   those read as a sticker and make the asset look smaller.
5. **Never call a cut done from a snapshot.** Sample the rendered mp4.

## ⚠ Sound: two things that will fool you
- **Gain is per SOUND.** Source peaks span 12 dB; one flat gain leaves half the pass inaudible.
  Measure each cue as a delta against the visual-only render.
- **Peak-delta saturates under speech.** A cue landing on a loud word will read as "thin" on
  `max_volume` however loud it really is — check `mean_volume` too, and trust the ear over the
  number. The same trap in reverse applies to the bed: **level it by LOUDNESS (LUFS), never by
  peak.** A -38 dB *peak* bed measured -49.8 LUFS against a -20.4 LUFS mix and was inaudible.
- **Four cues have leading silence and fire late** unless pre-rolled: `magic-reveal` 0.85s ·
  `whoosh` 0.50s · `ping` 0.25s · `swoosh` 0.15s.

