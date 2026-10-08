# What's in this skill — and what a buyer must supply themselves

This matters because the skill is sold. Some of what makes the format work is **method**, which
is yours to sell. Some of it is **third-party material** that happens to sit in the folder so the
blocks render on your machine — that part is not yours to redistribute, and shipping it inside a
paid product is the kind of thing that gets a product pulled.

Read this before packaging a release.

---

## ✅ Yours to sell — the actual product

This is the part that took a month and is genuinely hard to reproduce.

| | |
|---|---|
| `SKILL.md` | the format: the arc, the order of work, the five rules that get cuts rejected |
| `reference/*.md` | the standards. `BLACKLIST.md` alone is 17 entries, each one from a real rejection |
| `styles/*.json` | **three** editing presets — `house` (cream plate), `persa` (full bleed), `tierlist` (the board). `reference/STYLES.md` is the operative doc; each preset carries its own precondition, camera treatment, caption band and BLACKLIST deltas |
| `components/tier-board.html` | the tier board — measured geometry, the PRESENT-then-PLACE move, the re-rank, the slot math |
| `library/concepts.json` | 14 concepts mined from 22 scripts — trigger words, Show, Never |
| `scripts/*` | the whole toolchain, written here: the scout, the storyboard, the block renderer, the page shooter, the density gate, the SFX mixer, the bed layer, the pop-out matte |
| `ui-blocks/*.html` | the animated blocks, authored here — sessions-grid (5 modes × 3 fits), inbound-policy, page-highlight, skills-beat, skill-folder, ai-new-chat |
| `assets/tokens.css` | the design tokens |

## ⚠ NOT yours to redistribute — replace or license before selling

These are in the folder because the blocks and the mix reference them. They are other people's
work.

| what | where | the problem |
|---|---|---|
| **The bed** | `bgm/house-bed-loop.m4a`, `bgm/house-bgm-*.m4a` | a commercial music track by a named artist. A licence to *use* it in your own videos is not a licence to *redistribute* it inside a product you sell. |
| **The SFX palette** | `sfx/*` | a third-party pack. Check its licence — most forbid redistribution as a competing asset library, which is exactly what shipping the folder does. |
| **The mascot art** | `clawd/` (4.3 MB) | Anthropic's Claude character art. Trademarked, and not licensed for resale. |
| **Brand marks** | `brand/` — ChatGPT, Gemini, GitHub, Perplexity, X, Claude | third-party trademarks. Fine to show editorially in a video; not fine to ship as a bundled asset pack. |
| **Captured pages / UI** | `pages/`, `ui/`, `src-demo/` | screenshots of other people's products and documentation. |
| **Any sourced footage** | `videos/*/assets/broll/` | clips pulled from YouTube/X for a specific edit. Editorial use in one video ≠ redistribution. |

### The clean way to ship it

1. **Cut the media, keep the method.** Remove `bgm/`, `sfx/`, `clawd/`, `brand/`, `pages/`,
   `ui/`, `src-demo/` from the release. That drops it from ~31 MB to well under 1 MB and removes
   every rights question in one move.
2. **Ship a `SETUP.md`** telling the buyer to drop in their own bed, their own SFX pack and their
   own mascot/brand art at those paths. Every script resolves by path, so nothing breaks.
3. **Keep one royalty-free placeholder** per slot if you want it working out of the box — a
   CC0 bed and a CC0 SFX set — so the first render succeeds before they swap in their own.
4. **The mascots are the harder call.** They are load-bearing for the "agent" concept. Either
   commission your own character, or document that the buyer supplies one. Do not ship Anthropic's.

Nothing here is a legal opinion — but the split above is the obvious one, and it costs you almost
nothing because the value you are selling is the method, not the media.

---

## Machine dependencies the buyer needs

The skill assumes these exist on the machine; none of them ship in the folder.

- `node` + `npx hyperframes` — the HTML→MP4 renderer
- `ffmpeg` / `ffprobe` — every audio and video step
- `yt-dlp` — sourcing footage
- Python 3 with `playwright` (+ `chromium`) — the page shooter
- Google Chrome — `block-render.py` drives it headless
- The RVM matte env for the pop-out: `source library/.venv/Scripts/activate`
- `PATH` export, needed at every step:
  ```bash
  # Windows/Git Bash: node, npx, ffmpeg och python finns redan på PATH — ingen export behövs
  ```

## Verify a release before you send it

```bash
python scripts/verify-package.py        # every referenced path resolves; nothing dangling
```
