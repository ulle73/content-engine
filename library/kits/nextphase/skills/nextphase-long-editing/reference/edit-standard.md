# NextPhase LONG Edit Standard — EVERY long-form video follows this

The mandatory bar, on top of `structure.md` · `design-system.md` · `motion-grammar.md` ·
`editing-rules.md` · `sound-design.md` · `screen-recording.md` · `assembly.md`.

**Four non-negotiables: structure · editing/timing · media · sound.** Miss any one and the
edit is not done. (The short has three; long form adds **structure**, because at this length
an edit with great beats and no spine still loses the viewer.)

---

## 0 · Shot structure
Follow the arc in `structure.md`: cold open → payoff spike → promise → chapters with re-hooks
→ the turn → recap → CTA. Get `PLAN.md` approved before authoring.

## 1 · Editing & timing
- **RETENTION FIRST — no dead air, ever.** The cold open (0–15s) must have real media and
  motion from second one — never a lone static title, never a small dark screenshot with a
  highlighter on it (unreadable at this scale, and rejected).
- **Retention budget** (from `structure.md`): new visual beat ≤8s · uninterrupted face ≤12s ·
  same layout ≤25s · re-hook ≤90s · one graphic ≤10s.
- **Tighten first.** `scripts/tighten-cuts.py` before any timing work. `transcript-tight.json`
  is then the only timing source. Timing against the untightened transcript is the #1 way this
  edit goes wrong.
- **Anchor every graphic to a real word onset.** It enters ON, or a hair after, the exact word
  it illustrates — never before. **Round-number timings are banned.**
- Exit at the OUT word + 0.3s. One idea on screen at a time. Every entrance has a paired exit.
- **Verify transcript coverage vs file duration, minute by minute**, before editing. Parakeet
  has silently dropped audio (13s, once). On a long file a dropped chunk in the middle desyncs
  everything downstream and is easy to miss at the ends.
- Fix obvious ASR errors (tool/brand names, the CTA keyword, verbal number slips) while keeping
  sync.

## 2 · Media — real resources, not typeset text
- **Every supporting beat is a real resource.** Screenshot, real product UI, repo card, real
  footage, docs page, pricing page, tweet. Captions and the lower third are the only text; the
  CTA card is the one exception. Typeset text cards as *support* are banned — they are not
  interesting to watch and they are not proof.
- **Quota: ≥1 real media per 25s of finished video, minimum 10.** A 10-minute video needs ~24,
  a 15-minute one ~36. Prefer real **video** > screenshots > cards.
- **Match the thing to the word.** "on GitHub" → that repo's OG card. "TikTok" → a real TikTok,
  phone-framed. A named tool → its real UI. A stat → its source page. On the word, not 20s later.
- **No stock or podcast humans as b-roll** unless that person IS the subject of the line (the
  tool's creator on record, a named speaker being quoted). Otherwise the real UI, repo card,
  docs page or the project's own diagram. Never a generic cutaway to fill a slot.
- **NEVER use emojis** anywhere on screen — not in cards, chips, flows, warnings, CTAs, or
  captions. Build designed marks: a monogram in a coral circle, CSS icons/arrows/checks, small
  SVG. Emojis read as amateur.
- **ARTICLE-HIGHLIGHT** for any referenced headline/stat/quote/claim: screenshot the **real**
  article body, present it as a browser page, sweep a yellow highlighter across the **actual
  words** in sync with the voice. Real screenshot + real words only — never re-typeset, never
  invent. `components/article-highlight.html`.
- **Check every screenshot actually rendered content** before using it. Login-walled and
  JS-heavy pages come back blank and ship as empty panels.
- **Normalise every sourced clip to 30fps CFR** before it enters a composition.
- **Verify facts while sourcing.** Flag anything unverifiable, a dead or renamed product, or a
  third-party clip whose rights are unclear — BEFORE it can reach a render.

## 3 · Layout rotation
- **Never the same layout twice in a row. Never hold one past ~25s.** Six layouts:
  Full-Frame Face · Transparent Background · Split (Media Left) · Split (Face Left) ·
  Screen-Share + Bubble · B-Roll takeover.
- **Every layout change carries a transition AND a sound.** No silent cuts, ever.
- B-Roll content is **web-sourced by default**; a designed animation only when the subject IS
  the tool (Claude, a product UI, a pipeline you're explaining).

## 4 · Sound — two passes on the locked render
- **⭐ Payoff spike = `riser`, ALWAYS**, starting ~1.5s before the reveal so it crests on it.
  Also into every chapter card.
- **Density ~12–20 cues per minute.** Nearly every move earns a sound; silence is a deliberate
  breath. **Vary the palette** — match the sound to the specific element.
- **Every card exits on soft air** (`whoosh-2`/`swoosh`, ~0.07–0.09) so it breathes out instead
  of clicking off. Media cut-ins: `camera-shutter` in / `swoosh` out. Code/terminal: `keyboard`.
  Count-ups: `beep` ticks + `confirm` on landing. Hero reveal: `magic-reveal`.
- **A ducked MUSIC BED under the whole video** (`mix-bgm.sh`), ~22–26 dB under voice peaks.
  Change it at the turn; drop it ~3s before the payoff spike so its return is felt.
- **Calibrate to the VO** (`ffmpeg -af volumedetect`): SFX ~13–15 dB under voice peaks.

## Definition of done
`PLAN.md` approved · tightened · rendered per segment at `--quality high --fps 30` · concatenated ·
**≥1 real media per 25s** · **every graphic word-synced to the tight transcript** · facts checked ·
SFX pass + music bed · `chapters.txt` + `.srt` delivered · opened for review.
**Nothing publishes without explicit approval.**
