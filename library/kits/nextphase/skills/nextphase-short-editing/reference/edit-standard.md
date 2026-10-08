# NextPhase Edit Standard — EVERY short follows this

The mandatory bar on top of `design-system.md` · `motion-grammar.md` · `editing-rules.md` · `sound-design.md`.
Three non-negotiables: **editing/timing · media · sound.** If an edit misses any of these, it is not done.

## 0 · Shot structure — the anatomy of EVERY short
Follow this arc on every video (durations are defaults — adjust to the recording):
1. **Hook** (0 → end of the hook line): camera in the bottom card, a hook title in the top zone, a **`riser` building** underneath.
2. **Hook payoff** (on the punch word): **reveal** (scale/blur-in) **+ a coral flash cut**, the `riser` crests. ← the fixed signature.
3. **Full-screen face hold (~2.0s)**: the camera scales to fill the ENTIRE 1080×1920 frame, top-zone graphics cleared, **captions keep running**. A breath / eye-contact beat right after the hook.
4. **Body**: camera shrinks back to the bottom card (~50%); resume the normal house style — word-synced top-zone graphics + ≥4 real media + dense sound.
5. **Mid full-screen B-ROLL takeover (~3–4s, around the middle)**: ONE b-roll clip fills the ENTIRE frame (covers camera + graphics), **captions stay** — it reads like he's narrating over footage (the "explainer" beat). Then cut back to the card + body.
6. **1–2 extra full-screen FACE beats (~2–3s), placed where they fit** — an emphatic delivery line or a direct-to-camera warning ("here's the catch"). Same rules as the hook hold: face fills the frame, top graphics clear, captions stay.
7. **CTA** close (Comment "KEYWORD").

### Full-screen face ZOOM (only when the face is full-screen — never on the bottom card)
Every full-screen face beat gets a slow zoom on the camera. Pick from the approved three (`demo/zoom-menu/`):
- **Slow Push** (default) — scale 1.00 → 1.10, `ease:"none"`, origin `50% 46%`. The post-hook hold uses this.
- **Face Punch** — scale 1.00 → 1.20, `ease:"power2.inOut"`, origin `50% 38%` (into the eyes). For the intimate / warning beat.
- **Handheld Drift** — scale 1.08 → 1.12 + a small sine x/y sway. For a cinematic delivery line.
Zoom the full-frame camera element only (a supported transform); **captions ride on top and do not zoom.**

### PUSH transition on top-zone graphic swaps
Whenever a top-zone graphic changes, it **pushes**: the outgoing one slides out-left (`x:0 → -540`, fade), the incoming one slides in from the right (`x:540 → 0`, fade, `ease:power3.out`, ~0.44s). **Applies to top-zone graphics only** — never the caption band, never the camera. Staggered lists push their rows in one by one.

## 1 · Editing & timing
- **RETENTION FIRST — no dead air, ever.** The hook (0–~8s) MUST have web media + animation from second one (a real headline/screenshot flashing in, a "BREAKING" tag, a highlight sweep) — never a lone static title. **Nothing static holds longer than ~4s:** keep swapping graphics, and give screenshots motion (slow zoom/Ken-Burns), stats a **count-up**, lists a stagger. When he names a tool/company (OpenAI, ChatGPT, a site), show THAT real thing **on the word**, not 20s later. No long full-face or text-only stretches — cut, swap, animate, transition, sound. Long videos still need a new visual beat every few seconds.
- **Anchor every graphic to the transcript word onset.** It enters ON — or a hair AFTER — the exact word it illustrates, **never before it.** The "300" number appears when he says "300"; the TikTok card appears when he says "TikTok". **Round-number / eyeballed timings are banned** — pull the real word time from `transcript.json`.
- Exit at the OUT word +0.3s. ≤6s per graphic. One idea on screen at a time. Respect the safe zones (top zone 0–800 · caption band 820–940 · camera card 960–1920).
- **Verify transcript coverage vs file duration before editing** — Parakeet has silently dropped audio (lost 13s once). Re-transcribe any gap window and merge.
- Fix obvious ASR errors in captions (tool/brand names, the CTA keyword, verbal number slips) while keeping karaoke word-synced.

## 2 · Media — "get things online" (≥ 4 real, video-preferred) + designed b-roll
- **Two distinct layers, both required:**
  1. **Real web-sourced media — ALWAYS present, as inline cards (never the full-screen takeover).** ≥ 4 real per short: repo/OG cards, real clips (browser/phone-framed), screenshots, tweets. These are the "get things online" proof.
  2. **The full-screen B-ROLL takeover is WEB-SOURCED BY DEFAULT** (updated 2026-07-29 on Jad's direction — this reverses the earlier "designed only" rule). The takeover shows the real thing from the internet: the article page, the repo, the real clip, the pricing page. A **designed** HyperFrames graphic is the takeover only when the subject IS the tool (Claude, a product UI) — then it should look polished and on-brand.
  Captions during a takeover sit BELOW the media and never overlay it.
- **NEVER use emojis** anywhere on screen — not in cards, chips, flows, warnings, CTAs, or captions. Build designed marks instead (monogram in a coral circle, CSS icons/arrows, small SVG). Emojis read as amateur.
- **ARTICLE-HIGHLIGHT technique** (`system/components/article-highlight.html`): whenever Jad references a real headline, stat, quote, or claim, **browser-screenshot the REAL article body** and show it **filling the 9:16 frame like a white browser page** (slim chrome bar with the real URL up top), then sweep a **yellow highlighter (mix-blend multiply, like a real pen) across the actual words in sync with his voice** — each highlight rect positioned in % over its phrase (nudge until it hugs the words), scaleX animated from the transcript word onset. Scatter 5–8 highlights across the paragraphs. Real screenshot + real words only, never re-typeset or invented. It's a full-screen b-roll takeover (captions drop low).
- **MINIMUM 4 real web-sourced media per short.** Prefer real **video** clips over images; both over text cards. Text cards are the connective tissue *between* real footage — never the whole video.
- **Match the platform to the word:** "TikTok" → a real TikTok (phone-framed); "on GitHub" → the repo (OG card); a named tool/person → footage of it; a stat → its source page.
- **How to source** (Chrome extension is flaky, so use these): WebSearch/WebFetch to find → `curl` for direct images + GitHub OG cards (`opengraph.githubassets.com/<x>/<owner>/<repo>`) → `yt-dlp` to pull real clips from X / TikTok / YouTube. Trim to ~4–6s, **credit on-card** (e.g. "TikTok · @handle"). Tight crops only — full-page screenshots are unreadable at card size.
- Reusable subjects live in `broll-library/<subject>/` (capture once, reuse). One-offs in the video's `assets/broll/`.
- **Verify facts while sourcing.** Flag anything unverifiable, a dead/renamed product, or a third-party clip's rights BEFORE it can post.

## 3 · Sound — dense & natural (see `sound-design.md`)
- **⭐ HOOK PAYOFF = `riser`, ALWAYS.** The instant the spoken hook ends, a `riser` swells into the first reveal + a transition. This is the fixed signature on every NextPhase short — start the riser ~1.5s before the reveal so it crests on it.
- **Dense pass:** nearly every move earns a sound (a short typically runs **25–40 cues**). Silence is a deliberate breath, not the default.
- **Varied palette** — don't lean on three; match the sound to the specific element.
- **Every card exits on soft "air"** (`whoosh-2`/`swoosh`, gain ~0.07–0.09) so it breathes out instead of clicking off.
- **Media cut-ins get `camera-shutter` IN / `swoosh` OUT.** Code/terminal → `keyboard`. Count-ups → `beep` ticks + a `confirm` on landing. A hero reveal → `magic-reveal`.
- **Calibrate to the VO** (`ffmpeg -af volumedetect`): SFX sit ~13–15 dB under voice peaks. Hot VO → ~0.12 transients; quiet VO → ~0.07.

## Definition of done
Rendered `--quality high --fps 30` + scored · **≥ 4 real media** · **every graphic word-synced** · facts checked · opened for review. Nothing publishes without explicit approval.
