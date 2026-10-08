# claude-animation-skill (buildwithhanif)

**Vad:** skill för handritad 2D-animation skriven som kod – node canvas + ffmpeg, ingen webbläsare,
ingen GPU, inga API-nycklar. Detaljbibel, riggar (myra, bönfigurer, chibi, insekt), pensel/akvarell,
texturer, low-poly, action-fx och syntetiserat ljud (sound/music/ambient/chiptune).
**Licens:** MIT. Skillen är kopierad till `skill/` (med `LICENSE`) **utom** riggen
`lib/rigs/critter.mjs` (en Clawd-lik maskot) och `examples/` (Claude-figurer). SKILL.md nämner
critter – den finns alltså inte här.
**Hur vi använder det:** som motor för storybook-/handritade explainers och som ljudverktyg
(`sound.mjs`, `music.mjs`) i andra pipelines. Installera beroenden lokalt:
`cd library/external/claude-animation-skill/skill && npm install` (lägger node_modules här).
Kan flyttas till `.claude/skills/claude-animation/` av orkestratorn om den ska laddas automatiskt.
**Lokal sökväg:** `C:\Users\rydqv\video-tools\claude-animation-skill` (commit 4ddb8c8).
