# opus55-videos-yihui (yihui-dev/awesome-opus5-5-videos)

**Vad:** samling med 703 prompts som skapare använt för att få Claude Opus 5.5 att koda virala
videor (HTML, Canvas, SVG, Three.js, GSAP, GLSL). 418 av dem har en levande remake på Skillry
bredvid originalet. Kategorier: motion graphics, explainers, 3D-scener, spel/interaktivt.
**Inte samma** som `library/external/awesome-opus-5-5-videos` (athemeroy), som är en
forskningsöversikt med egna mallar.

**Licens:** repot är MIT, men prompterna är skrivna av respektive skapare på X. Vi följer samma
linje som `awesome-ai-motion`: **tredjepartsprompts länkas, kopieras inte.** Posterna här har egna
svenska sammanfattningar och pekar på prompten i originalrepot och skaparens inlägg.

**Hur vi använder det:** sök med `find.py` (t.ex. `"3d explainer"`, `"partiklar"`, `"kinetisk typografi"`),
öppna prompten via länken och använd den som **förebild** för hur man formulerar en kodad animation –
skriv sedan vår egen prompt för bolaget. Ta aldrig över skaparens text, bilder, ljud eller varumärken
rakt i reklam.

**Innehåll i katalogen:**
- `ext.opus55-videos-yihui.gallery` – hela galleriet på Skillry (original bredvid remake).
- `ext.opus55-videos-yihui.cat-*` – en post per kategori.
- `ext.opus55-videos-yihui.<slug>` – de 83 utvalda (README-urvalet, en per distinkt prompt) med
  svensk sammanfattning och taggar.

**Källa:** https://github.com/yihui-dev/awesome-opus5-5-videos (data hämtad 2026-10-30,
`data/videos.json`). Status `unverified` tills något renderats här och granskats.

**Uppdatera:** hämta ny `data/videos.json` och kör `make_library.py` (instruktion i skriptets
huvud), sedan `python library/tools/build_catalog.py --check`. Sammanfattningarna i
`summaries.json` är våra egna; nya utvalda poster behöver en egen sammanfattning där.
