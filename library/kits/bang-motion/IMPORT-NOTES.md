# Import: bang-motion

**Källa:** https://github.com/bangtutorial/bang-motion, v1.19.0, commit `c1aa65e` (MIT, © 2026 Bang Tutorial).
**Importerad:** 2026-11-07 av Claude på begäran av Jonas. Skillen ligger i `.claude/skills/bang-motion/`, kitets index i
`LIBRARY.json` (53 poster), upphovspersonens exempelbilder (fiktiva varumärken, nedskalade till 1280 px) i `gallery/`.
Den tidigare pekarposten `ext.awesome-claude-video-skills.bang-motion` hänvisar hit.

## Vad som togs med
- `SKILL.md` är ny: svensk ingång som säger vad som gäller i content-engine. Originalet (indonesiska) ligger orört i
  `references/ORIGINAL-SKILL.md`.
- `references/`: anti-ppt, architecture, explainer, kartun-panggung, opener-konsep, roadmap, techniques (orörda, indonesiska).
- `assets/`: sju startfiler (orörda) + `exempel-gk-9x16.html` med `exempel-gk-assets/` (vårt eget test, se nedan).
- `scripts/`: snap.mjs, export-frames.mjs, serve.py, vo-pauses.html, kepala-ekspresi.py + ny `run.sh`. `LICENSE`, `CHANGELOG.md`.

## Borttaget / ändrat
- **After Effects-bryggan** (`references/ae-bridge-higgsfield.md`, `scripts/ae/`) borttagen – kräver AE och Higgsfield (betalt).
- `.claude-plugin/`, `README.md`, ikoner och installationsinstruktioner (global klon till `~/.claude/skills`) inte med.
- `snap.mjs` och `export-frames.mjs`: `puppeteer` → `puppeteer-core` med installerad Chrome (`CHROME_PATH`).
  `export-frames.mjs` tar bredd/höjd från sidan (`OPENER.W/H`) i stället för hårdkodat 1920×1080, så 9:16 exporteras rätt.
- `run.sh` (ny): installerar `puppeteer-core@24` lokalt i `work/bang-motion/_tools` (gitignorerat), kör snap/export och
  gör MP4 med ffmpeg. Inget globalt.
- Higgsfield nämns fortfarande i referenserna som bildkälla – SKILL.md säger att egna bilder går först och betalt bara efter fråga.
- Våra regler (9:16, safe zones, läsregel, Spotlight-slutbild, ljud, faktabank) står över originalets i SKILL.md.

## Verifiering (2026-11-07)
- Alla sju startfiler renderade med `run.sh snap` vid t = 3 s och granskade → `library/previews/bang-motion.starter.*.jpg`.
  De visar startfilernas platshållare (GANTI), som förväntat.
- GK-test 9:16 (`assets/exempel-gk-9x16.html`): Sankt Jörgen-banfoto, "Golfare i Göteborg?", kontinuerlig kamera,
  tecken-för-tecken-rubrik med riktad oskärpa, loggan landar. Exporterad med `run.sh export` → 1080×1920, 222 bildrutor
  (7,4 s, 30 fps), avkodad utan fel, kontaktark granskat → `library/previews/bang-motion.skill.bang-motion.{jpg,mp4}`.
  Två fel hittades och rättades i testet (ljus kant när kameran panorerade; mörkläggningen hamnade över loggan).
- Testet är ett **tekniktest**, inte en annons: ingen musik, ingen Spotlight-slutbild, och det klarar inte Bang Motions eget
  PPT-test fullt ut (kamerarörelse + text är enda rörelsen).
- Stilar, koncept och de flesta effekterna är bara beskrivningar i referenserna → `unverified`.

## Kända begränsningar
- Referenserna är på indonesiska; agenter läser dem, men SKILL.md har en ordlista och en innehållskarta.
- Startfilerna laddar GSAP/Three.js/typsnitt från CDN – exporten kräver nätverk.
- Ingen ljudhantering: exporten är tyst, ljud läggs på MP4:an enligt `skills/ljud`.
