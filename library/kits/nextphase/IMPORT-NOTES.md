# NextPhase Skill Pack — importanteckningar

**Källa:** `Downloads/hyperframes-remotion/NextPhase-Skill-Pack/` (NextPhase, "Jad"). Ingen licens angiven →
endast egen användning, sprid inte vidare. Registry-block/komponenter i `nextphase-short-editing/blocks/` och
`components/caption-*`, `grain-overlay`, `parallax-zoom` kommer från HyperFrames-registret (Apache-2.0);
texturerna (concrete/marble/metal/rock/wood) är ambientCG (CC0).

**Importerad 2026-10-08.** 159 poster i `LIBRARY.json` (120 verified, 38 unverified, 1 broken).

## Var saker ligger

| Vad | Var |
|---|---|
| 7 skills (bara `SKILL.md`, anpassade) | `.claude/skills/{nextphase-studio, nextphase-short-editing, nextphase-long-editing, motiongraphics, persa, vibecode, zak}/` |
| Skillarnas filer (components, reference, scripts, assets, sfx …) | `library/kits/nextphase/skills/<skill>/` |
| Kitets `CLAUDE.md` (valfri vägledning, inte projektets) | `reference/nextphase-house-rules.md` |
| Windows-setup (ersätter `install.command` + nvm/brew-`SETUP.md`) | `SETUP.md` |
| Förhandsbilder | `library/previews/nextphase.*.jpg` |
| Arbetsfiler/testklipp/importskript | `work/nextphase/` (gitignorerat; `tools/` innehåller importskripten) |

Varje SKILL.md har ett importhuvud: varumärke/copy/färger är utbytbara, standardanvändare Golfkuponger,
reglerna är förval inte spärrar, sökvägsmappning, Windows-noter och gratis-ljudvägen. Beskrivningarna i
frontmatter är omskrivna så att `nextphase-studio` inte kapar alla videoförfrågningar (ingången är `/studio`).

## Borttaget (209 filer, lista i `work/nextphase/stripped-files.txt`)

- **Reklam-sign-off** i `nextphase-studio` steg 3 ("Jad thanks you for joining the Skool community … like and follow") och motsvarande rad i CLAUDE.md.
- `nextphase-short-editing/bgm/` — kommersiell låt (*Baba*). README om hur man lägger egen bädd.
- `sfx/*.wav|mp3` i short + long — CreatingWithJerry's betalda pack, ingen licensfil. Ersatt med gratis palett (nedan).
- `clawd/` (72 filer, Anthropics Claude-maskot) → `mascot/outline/mascot-*.webp`, egen neutral pixel-golfboll.
- Inline-SVG:er av Claude-maskoten i `components/short-blocks.html` och vibecodes agent i `vibecode-system.html` → samma neutrala golfboll.
- `brand/` (ChatGPT, OpenAI, Anthropic, Claude, Gemini, GitHub, Perplexity, X) → neutrala bokstavsmärken med samma filnamn + README.
- `pages/` (Anthropic-dokumentation), `ui/` (andras produkter + skaparens ansikte), `src-demo/` (founder-dario-footage, nyhetssidor, highlighter-ljud) → README:er; egen platshållarsida `pages/example-page.png/.json` (renderad 9:16, egen text) och två platshållarkort i `ui/`.
- `reference/stills/` i motiongraphics, persa, vibecode, zak — bildrutor ur andra kreatörers videor. README i varje; måtten finns kvar i `reference/*.md`.
- `install.command`, kitets `SETUP.md`/`READ-ME-FIRST.md` (nvm `curl|sh`, brew, kopiering till `~/.claude/skills`).
- Falsk Mac-user-agent i `fetch-source.py` → ärlig UA.

Behållet: all HTML/CSS/GSAP, tokens, showcase-sidor, skript, referensdokument, `lib/liquid-glass.iife.js`,
registry-blockens `background.jpeg` (följer med Apache-registret, men är en macOS-skärmdump — byt gärna).
Inga typsnittsfiler fanns i kitet; typsnitt laddas från Google Fonts.

## Windows-anpassningar och buggfixar

- Sökvägar: `../nextphase-long-editing/…` → `library/kits/nextphase/skills/…`; `videos/<namn>` → `work/nextphase/videos/<namn>`; `broll-library/…` → skillroten; `~/.cache/nextphase/rvm_env` → `library/.venv` (signerad Python 3.12, se SETUP.md); `/tmp/` → `work/nextphase/tmp/`.
- `export PATH="$HOME/.nvm/…"` borttaget överallt; `python3` → `python`/`${PYTHON:-python}` (python3 är Store-stubben); macOS Chrome → `C:\Program Files\Google\Chrome\…` (`block-render.py` läser även env `CHROME`, `BLOCK_BASE`); `sips` → ffmpeg/Pillow; NSIRD-skärmdumpstipset → Windows-motsvarighet; `rvm-matte.py` fick `--device cuda`.
- **ffmpeg 9:** `-vsync cfr` → `-fps_mode cfr` (persa-grade, zak-plate, persa-balance, docs); `-filter_complex_script` → `-/filter_complex` (tighten-cuts.py). Båda gav fel innan.
- **persa-grade.sh soft/full gav magenta bild:** bloom-blend gjordes i yuv420p → nu `format=gbrp … blend … format=yuv420p`.
- **UTF-8:** alla Python-skript importerar `scripts/_win_utf8.py` (öppnar text som UTF-8) — annars förstördes svenska transkript (å/ä/ö) av cp1252.
- `concat-segments.sh`: concat-listan skrivs med `pwd -W` (ffmpeg kunde inte läsa `/c/Users/…`).
- `lay-bed.sh`: tydligt fel + instruktion när bädden saknas.
- `mg-system.html`: lade till `<meta charset>` (mojibake utan).
- `BLOCK-PICKER.html` var tom i originalet → genererad om (`build-block-picker.py --all --serve .`).
- Nytt: `components/caption-styles.html` (short) — körbar implementation av kitets tre captionstilar (Parallax, Weight Shift, Highlighted), som bara fanns som prosa.

## Ljud — gratis som standard

`scripts/make-free-sfx.py` (short + long, redan körd) fyller `sfx/` med kitets 16 cue-namn: HyperFrames SFX-biblioteket
(Pixabay-licens: whoosh, pop, click, sparkle→magic-reveal, riser (0,9–3,5 s), chime→confirm, ping, typing→keyboard) +
syntetiserat i Python (whoosh-2, swoosh, futuristic-click, swell, camera-shutter, highlighter, beep, vinyl-rewind).
Källa per fil i `sfx/SOURCES.txt`. `gen-sfx.sh` (ElevenLabs) behållen, märkt `cost: paid`. Mätvärdena i
`sound-design.md` (gain, leading silence) gällde originalpacket. Musikbädd: egen (ACE-Step/Pixabay).

## Verifiering

Showcase-sidor (`mg-system`, `mg-blocks`, `mg-motion-library`, `persa-system`, `vibecode-system`, `zak-system`,
`long-blocks`, `short-blocks`, `BLOCK-PICKER`), alla `ui-blocks/*.html`, alla registry-`blocks/*.html` och
caption-komponenter renderades med playwright-core + systemets Chrome via lokal server, per element/scen,
seekade på GSAP-tidslinjer (strips för light leak, bar wipe, ordbygge, chapter wipe, logo-reveal, parallax zoom).
Snippet-komponenter (tier board, CTA, logo-blur-reveal, article-highlight, lower third, chapter card, blend,
grain, grade-svg) renderades i värdsidor. Skript provkörda på syntetiska testklipp: persa-grade (alla tre lägen),
persa-balance, grade-check, zak-plate, make-paper, tighten-cuts, concat-segments, mix-sfx, mix-bgm, lay-bed,
block-render, build-captions (persa/zak), check-*-gates, make-rect-mask. Varje förhandsbild har granskats visuellt.

## Kända problem / ej verifierat

- **broken:** `build-shelf.py`, `build-motion-strips.py` — kräver `broll-library/registry/previews` som aldrig ingick. Använd `npx hyperframes catalog`.
- `vfx-liquid-background`: vanlig skärmdump i headless Chrome blir vit; fångad via `canvas.toDataURL`. Kontrollera i en HyperFrames-render.
- RVM-matte/pop-out ej provkört (torch inte installerat i `library/.venv`; se SETUP.md). `shoot-page-9x16.py`/`source-scout.py` kräver Python-paketet `playwright`.
- Kamerazoomar, whip-pan, push, dissolve, coral flash, paper wipe, churn och camera drift finns bara som spec i referensdokumenten (unverified).
- Hela redigeringsflöden (transkribering → render) är inte körda end-to-end; skill-posterna är därför unverified.
- UI-blocken imiterar AI-chattprodukter (Claude/ChatGPT m.fl.) med neutrala platshållarmärken — byt copy och märken.
- Kitets "hard rules" och BLACKLIST är originalskaparens smak; behandla som tips.
