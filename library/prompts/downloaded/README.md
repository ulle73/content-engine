# Nedladdade prompts

Tredjepartsprompts som följde med nedladdningarna i `Downloads/hyperframes-remotion/`. Varje fil har
en svensk inledning (vad den gör, när den passar, hur den anpassas för Golfkuponger) och därefter
originaltexten **oförändrad** i ett kodblock. Texterna är referensdata: läs och anpassa, kör inte
stegen blint. Indexeras i `LIBRARY.json` (kit `prompts-downloaded`).

| Fil | Original | Innehåll |
|---|---|---|
| `30-days-of-content.md` | `30 Days of Content - THE PROMPT.txt` | Månadsplan: research → 30-dagarskalender → karuseller, manus, klipp → schemaläggning |
| `30-days-of-content-paste-version.md` | `prompt-1.txt` | Samma prompt, bara inklistringsdelen (dubbla radbrytningar) |
| `style-master-sheet.md` | `prompt-2.txt` | Stilark (16:9 design-system-board) ur en referensbild |
| `character-and-style-sheet.md` | `prompt.txt` | Karaktärsark (turnaround) + samma stilarksprompt |
| `links.md` | `links.txt` | Länklista: HyperFrames-promptguider och två GitHub-repon |

## Medvetet inte kopierat

Dessa filer är **installationsinstruktioner för kit** som importeras på annat håll (av
kit-importen i `library/kits/`, med Windows-anpassning och utan globala installationer):

- `INSTALL PROMPT (paste into Claude Code).txt` – installerar skillen *motion-studio* i
  `~/.claude/skills` och laddar ner musikmodellen ACE-Step (~15 GB). Kitet: `library/kits/motion-studio/`.
  Dess tre "prova nu"-exempel (showreel, lyrikvideo, berättarfilm) finns omskrivna som egna mallar i
  `library/prompts/motion-studio-playbook/`.
- `INSTALL PROMPT.txt` – installerar skillen *live-carousel* globalt. Kitet: `library/kits/live-carousel/`.
- `PASTE-INTO-CLAUDE-CODE.txt` – installerar *Carousel Kit* i projektroten och kör `doctor.py --fix`.
  Kitet: `library/kits/carousel-kit/`.

Enligt `library/IMPORTING.md` ska inget installeras globalt (`~/.claude`, `curl | sh`); kiten
används från repot.
