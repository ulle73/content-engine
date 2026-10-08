# Importregler för biblioteket (för agenter och människor)

Mål: allt material ska gå att hitta, välja och köra från content-engine. Varje mall, effekt,
övergång, textbehandling, karusellstil, skill och prompt blir en egen post i en `LIBRARY.json`
(format i `library/README.md`). Hellre för många, fint granulerade poster än för få.

## Var saker hamnar

| Vad | Var |
|---|---|
| Kitets Claude Code-skills (mappar med `SKILL.md`) | `.claude/skills/<skillnamn>/` — laddas automatiskt när Claude Code körs i repot |
| Kitets övriga filer (mallar, scripts, komponenter, referenser, exempelbilder) | `library/kits/<kit>/` |
| Kitets index | `library/kits/<kit>/LIBRARY.json` |
| Kitets egen dokumentation om importen | `library/kits/<kit>/IMPORT-NOTES.md` (källa, vad som togs bort, Windows-anpassningar, kända problem) |
| Förhandsvisningar | `library/previews/<id>.jpg` (max ~1280 px bred) och ev. `library/previews/<id>.mp4` (max ~2 MB, 480–720 px) |

Skillnamn måste vara unika i `.claude/skills/`. Om två kit har samma `name:` — byt till ett
beskrivande namn (t.ex. `carousel-kit`, `carousel-generator`) i både mappnamn och frontmatter.

## Sökvägar

Skills och scripts pekar ofta på `~/.claude/skills/<namn>/…`, `~/Downloads`, `~/<något>` eller
en projektrotsmapp. Skriv om till repo-relativa vägar: skillen ligger i `.claude/skills/<namn>/`,
kitfiler i `library/kits/<kit>/`, och arbetsfiler/utdata skrivs till `work/<kit>/…` (gitignorerat)
— aldrig till användarens hemkatalog.

## Ta bort / ändra

- **Uppladdning av användarens filer till tredje part** (t.ex. `upload.py` mot catbox.moe / 0x0.st): ta bort och ersätt med lokal fil eller avstängd stub som förklarar.
- **Bot-detekteringsundvikande** (falsk user-agent, dölja automationsflaggan): ta bort; vanlig Playwright.
- **Reklam/krav på sign-off** (t.ex. "Jad thanks you … like and follow"): ta bort.
- **Media som inte får spridas eller inte är vårt**: kommersiell musik, tredjeparts SFX-paket utan licens, andras logotyper/maskotar (t.ex. Anthropic/Claude-figurer), skärmdumpar och demo-footage av andra personer. Lämna en `README` i mappen om vad som saknas och hur man ersätter det.
- **Installationsscripts som ändrar användarens system** (`curl … | sh`, globala installs i `~/.claude`, `brew`, macOS `install.command`): ersätt med en Windows-vänlig `SETUP.md` / `setup.ps1` eller instruktioner i skillen. Installera inget globalt.
- **Projektregler som tvingar frågor/stil** (t.ex. kitets `CLAUDE.md`): flytta in som referens i kitet, inte som projektets `CLAUDE.md`. Stilregler är *tips*, aldrig spärrar.
- **Betalda API:er** (kie.ai, ElevenLabs, Higgsfield …): behåll men märk posten `cost: "paid"` och `requires: ["api:<tjänst>"]`; gratisvägen ska vara standard.

Behåll: kod, HTML/CSS/GSAP-mallar, komponenter, referensdokument, tokens, typsnitt med öppen licens (OFL m.fl.), egna exempelbilder som kitet själv skapat.

## Windows

Maskinen: Windows 11, Git Bash, Node 24, ffmpeg 9, Chrome i `C:\Program Files\Google\Chrome\Application\chrome.exe`,
Python 3.14 (`python`) och signerad Python 3.12 i `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`.
**Smart App Control blockerar DLL:er i uv-nedladdade Python-byggen** — skapa venv med den signerade
3.12:an (`…\Python312\python.exe -m venv library/.venv`), inte `uv python install`.
Inga macOS-verktyg: ersätt `sips` med Pillow, Apple Vision-frilägg (`cutout.swift`) med
`npx hyperframes remove-background` eller `rembg`, `open` med `start`, `/Applications/Google Chrome.app` med Chrome-sökvägen ovan.
HyperFrames CLI: `npx hyperframes` (finns). Skript som bara går på Mac och inte kan portas: märk posten `broken` och förklara i `notes`.

## Verifiering

`status: "verified"` får bara sättas när du **renderat** något (stillbild eller video) och **tittat på det**
(Read-verktyget kan visa bilder) och det ser rätt ut. Lägg filen i `library/previews/` och peka på den
i `preview`. Annars `unverified`. Fungerar det inte: `broken` + orsak.

## Git

Kör inga git-kommandon som ändrar något (ingen commit, checkout, reset, push). Orkestratorn committar.
Skriv bara i dina tilldelade mappar.

## Klart när

`python library/tools/build_catalog.py --check` visar 0 problem för dina poster.
