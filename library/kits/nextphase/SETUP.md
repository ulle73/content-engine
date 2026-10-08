# NextPhase-kitet — setup på Windows

Ersätter kitets macOS-`install.command` och `SETUP.md` (nvm via `curl | sh`, `brew`, kopiering till
`~/.claude/skills`). Här installeras **inget globalt**: skillsen ligger redan i repots `.claude/skills/`
och laddas när Claude Code körs i content-engine. Kör allt från repo-roten i **Git Bash** (eller
PowerShell där det står).

## 1. Det som redan finns på maskinen

| Verktyg | Kontroll | Används till |
|---|---|---|
| Node 24 + `npx` | `node -v` | HyperFrames (`npx --yes hyperframes …`) — render, lint, snapshot, transcribe |
| ffmpeg / ffprobe (winget Gyan.FFmpeg) | `ffmpeg -version` | allt klipp, mix, grade, concat |
| Chrome | `"/c/Program Files/Google/Chrome/Application/chrome.exe" --version` | headless-skärmdumpar, `block-render.py` |
| Python | `python --version` | skripten (Pillow behövs för vissa) |
| Signerad Python 3.12 | `"$LOCALAPPDATA/Programs/Python/Python312/python.exe" --version` | venv för RVM-matte |

Använd `python`, aldrig `python3` (på den här maskinen är `python3` Microsoft Store-stubben).
Inga PATH-exporter behövs — kitets `export PATH="$HOME/.nvm/…"`-rader är borttagna.

## 2. Python-paket för skripten (lätta)

```bash
python -m pip install --user pillow numpy opencv-python
```

Valfritt, bara för sidfångst-skripten (`shoot-page-9x16.py`, `source-scout.py`):

```bash
python -m pip install --user playwright      # använder systemets Chrome via channel/executable
```

`yt-dlp` (källklipp från X/YouTube/TikTok) — valfritt: `python -m pip install --user yt-dlp`.
Respektera rättigheterna till klipp du hämtar.

## 3. RVM-matte (pop-out / huvudet-framför-texten) — valfritt

Behövs bara för layouter där personen frilagts: short-housens pop-out, persa (text bakom huvudet),
vibecode agent-beat, long-formens Transparent Background. **Smart App Control blockerar DLL:er i
uv-nedladdade Python-byggen** — skapa venv med den signerade 3.12:an:

```bash
"$LOCALAPPDATA/Programs/Python/Python312/python.exe" -m venv library/.venv
library/.venv/Scripts/python.exe -m pip install --upgrade pip
library/.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
library/.venv/Scripts/python.exe -m pip install opencv-python numpy pillow av tqdm
```

Kör sedan t.ex.:

```bash
library/.venv/Scripts/python.exe library/kits/nextphase/skills/nextphase-long-editing/scripts/rvm-matte.py \
  --src work/nextphase/videos/<namn>/assets/recording-tight.mp4 --out work/nextphase/videos/<namn>/frames_rvm --frames 150
```

Första körningen hämtar RVM-modellen via `torch.hub` från GitHub (PeterL1n/RobustVideoMatting, ~15 MB).
Maskinen saknar NVIDIA → `--device cpu` (standard, ~0,25 s/bildruta i 1080p).
Lättare alternativ utan torch: `npx hyperframes remove-background`.

## 4. Ljudpaletten (gratis)

```bash
python library/kits/nextphase/skills/nextphase-short-editing/scripts/make-free-sfx.py
python library/kits/nextphase/skills/nextphase-long-editing/scripts/make-free-sfx.py
```

Fyller `sfx/` med HyperFrames SFX-biblioteket (Pixabay-licens, finns i `~/.claude/skills/media-use/…`)
och syntetiserade ljud för resten. Redan körd vid importen. `scripts/gen-sfx.sh` (ElevenLabs) är
**betald** och valfri.

Musikbädd: ingen följer med (originalet var en kommersiell låt). Generera en instrumental loop
gratis lokalt med ACE-Step eller använd en Pixabay-låt; lägg den per video i
`work/nextphase/videos/<namn>/assets/music/bed.mp3` (long) eller som 3:e argument till `lay-bed.sh` (short).

## 5. Förhandsvisa komponenterna

Showcase-sidorna öppnas direkt i Chrome (`start library\kits\nextphase\skills\motiongraphics\components\mg-system.html`
i PowerShell). Typsnitt och GSAP laddas från Google Fonts / CDN, så nätet behövs. UI-blocken i
`nextphase-short-editing/ui-blocks/` hämtar `../brand/`-, `../mascot/`- och `../pages/`-filer — öppna dem via
en lokal server om Chrome blockerar `fetch` från `file://`:

```bash
cd library/kits/nextphase/skills/nextphase-short-editing && python -m http.server 8777 --bind 127.0.0.1
# http://127.0.0.1:8777/BLOCK-PICKER.html   eller   …/ui-blocks/page-highlight.html?fit=full
```

## 6. Kontroll

```bash
node -v && ffmpeg -version | head -1 && python -c "import PIL, numpy; print('py ok')"
python library/tools/build_catalog.py --check
```
