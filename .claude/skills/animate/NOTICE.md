# Notice

This skill is **Animate** by cth9191 — <https://github.com/cth9191/animate> (plugin `animate` v0.4.0, imported from
commit `7e5eb56` of 2026-10-05), released under the MIT License (see `LICENSE` in this folder, copied unchanged from the
repository). Copyright (c) 2026 cth9191.

Imported into content-engine on 2026-10-07/08 (library kit `animate`). Changes made for this repo (all MIT-permitted):

- `tools/pw.mjs` (new): one Playwright loader for every tool — a local install in `work/animate/node_modules` instead of
  `npm i -g` — and a launcher that uses the system Chrome (no Chromium download), falling back to Playwright's Chromium.
- `setup.ps1` (new): Windows setup without global installs; optional faster-whisper in `library/.venv`.
- Every tool imports `launch()` from `tools/pw.mjs` instead of `chromium.launch()`.
- `build.mjs` / `gallery.mjs`: also find saved styles in `library/kits/animate/styles/`.
- `review.mjs`: reference images default to `work/animate/references/`; contact sheets for a non-main format now read
  that format's own `frames-<w>x<h>/` (upstream read the main format's frames).
- `export.mjs`: the narration-caption preview of a non-main format reads and writes its own files.
- `voice.mjs` / `voice_words.py`: `--lang sv` (multilingual whisper model), word matching keeps å/ä/ö, Python from
  `library/.venv` when present (`ANIMATE_PYTHON` overrides).
- Docs (`SKILL.md`, `intake.md`, `new-style.md`, `styles/README.md`): paths for this repo (`work/animate/pieces/`,
  `node .claude/skills/animate/tools/…`), check-ins and style rules as defaults rather than gates, ElevenLabs marked paid.
- Line endings normalised to LF.

Full import notes: `library/kits/animate/IMPORT-NOTES.md`.
