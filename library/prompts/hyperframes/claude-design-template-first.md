# Claude Design + HyperFrames: mallen först (svensk arbetsguide)

Destillat av HyperFrames-guiden *Claude Design + HyperFrames (Template-First)*
([original](docs/guides/claude-design-hyperframes.md), plus [Send-to-varianten](docs/guides/claude-design-send-to-hyperframes.md)),
omsatt till körbara mallar i `library/templates/hyperframes-skeletons/`. Allt här är **utgångslägen och tips**: du får bryta
mot vad som helst om det gör filmen bättre. Det enda som är hårda krav är de tekniska render-reglerna längst ner, och de
finns bara för att annars blir renderingen fel.

## Arbetsgången

1. **Välj skelett** efter videotyp (tabellen nedan). Kopiera mappen och kör `npx hyperframes lint` (ska ge 0 fel).
2. **Fyll identiteten** i `:root` (`--bg`, `--ink`, `--accent`, `--muted`, `--accent-dim`, `--font-display`, `--font-data`)
   och Google Fonts-länken.
3. **Fyll scenerna**: innehåll i `.scene-content`, dekor (glöd, korn, vinjett) direkt i scen-diven.
4. **Animera**: entré (`tl.from`) cirka 0,1–0,3 s in i scenen, plus *mid-scene activity*, alltså något som fortsätter röra sig
   efter entrén. Se [mönstergalleriet](../../templates/hyperframes-skeletons/pattern-gallery/).
5. **Övergångar**: välj shaders i [shadergalleriet](../../templates/hyperframes-skeletons/shader-gallery/). Räkna
   `time = scengräns − duration/2`.
6. **Förhandsgranska och rendera**: `npx hyperframes preview`, sedan `npx hyperframes render --quality draft`, titta, och till sist `render`.

| Typ | Format | Längd | Scener | Mall |
|---|---|---|---|---|
| Social reel | 1080×1920 (9:16) | 10–15 s | 5–7 | `a-social-reel` (15 s, 6 scener, 1 shader) |
| Lanseringsteaser | 1920×1080 (16:9) | 15–25 s | 7–10 | `b-launch-teaser` (25 s, 8 scener, 3 shaders + 1 crossfade) |
| Produktexplainer | 1920×1080 (16:9) | 30–60 s | 10–18 | `c-product-explainer` (45 s, 12 scener, 3 shaders + 4 crossfades) |
| Filmisk titel | 1920×1080 (16:9) | 45–90 s | 7–12 | `d-cinematic-title` (60 s, 7 scener, 6 shaders) |

## Promptmall för Claude Code (klistra in och fyll i)

```text
Använd /hyperframes. Utgå från mallen library/templates/hyperframes-skeletons/<a-social-reel|b-launch-teaser|c-product-explainer|d-cinematic-title>/
(kopiera till work/<projekt>/). Behåll strukturen (script-ordning, .scene.clip, .scene-content, HyperShader-kedjan).
Varumärke: <färger / typsnitt / länk till designspec>. Ämne: <vad filmen säger>. Längd: <s>. Format: <9:16/16:9/1:1/4:5>.
Scener: <scen 1: … / scen 2: … / …>. Spektakelbeat: <det ENDA överdrivna ögonblicket och var det sitter>.
Varje scen: entré + minst två rörelsemönster (räknare, SVG-streck, teckenstagger, andningsflyt, stapelfyllning,
omloppsbana, highlight-svep, Ken Burns, glödpuls). Shaders på <2–3 nyckelögonblick> (förslag: cinematic-zoom vid hero,
light-leak vid energiskifte, cross-warp-morph vid CTA). Kör lint, rendera draft, titta på frames och justera.
```

## Animationsmönster (avsnitt 8 i guiden, körbara i mönstergalleriet)

| Mönster | När | Kärnan |
|---|---|---|
| Räknare | statistik, priser | `tl.to(obj, { v: mål, onUpdate: skriv ut })` |
| SVG-streck | linjer, kurvor, logotyper | `stroke-dasharray = längd`, animera `strokeDashoffset → 0` |
| Teckenstagger | rubriker, ordmärken | `<span class="char">`, `stagger: { each: 0.05–0.12 }` |
| Andningsflyt | logga, CTA-knapp | `y: -5…-26, yoyo: true, repeat: 1, ease: sine.inOut` |
| Stapelfyllning | diagram | `scaleY: 0 → 1, transformOrigin: bottom`, 0,15 s förskjutning |
| Omloppsbana | prickar, ikoner | `rotation: 360`, `transformOrigin` i banans mitt |
| Highlight-svep | nyckelord | `background-size: 0% → 100%` på en linear-gradient |
| CSS-korn | analog känsla | radial-gradient-korn (inte SVG-filter-korn) |
| Ken Burns | stillbilder | `scale: 1 → 1.03–1.12`, `ease: none`, hela scenen |
| Glödpuls | bakgrund | opacity-puls på radial glöd |

**Easing-palett** (variera gärna, minst 3 per scen): smooth `power2.out` 0,4–0,6 s · snappy `power4.out` 0,2–0,3 s ·
bouncy `back.out(1.6)` 0,3–0,5 s · dramatic `expo.out` 0,3–0,5 s · dreamy `sine.inOut` 0,5–0,8 s · mechanical `steps(5)`.

## Övergångar (14 shaders)

`domain-warp`, `ridged-burn`, `whip-pan`, `sdf-iris`, `ripple-waves`, `gravitational-lens`, `cinematic-zoom`,
`chromatic-split`, `swirl-vortex`, `thermal-distortion`, `flash-through-white`, `cross-warp-morph`, `light-leak`, `glitch`.
Utelämna `shader` för en ren CSS-crossfade.

Guidens energikarta, som ett **förslag**:
lugnt/redaktionellt → cross-warp-morph, light-leak, domain-warp · professionellt → cinematic-zoom, whip-pan, sdf-iris ·
högenergi → glitch, chromatic-split, ridged-burn · eteriskt → gravitational-lens, ripple-waves, swirl-vortex.

## Smakråd (tips, inga regler)

Guiden har listor som den kallar "banned". Här är de omformulerade till smakråd. De motverkar "AI-standardlooken", men
du väljer själv:

- **Typsnitt som alla LLM:er tar till:** Inter, Inter Tight, Roboto, Open Sans, Noto Sans, Lato, Poppins, Outfit, Sora,
  Fraunces, Playfair Display, Cormorant Garamond, EB Garamond, Syne, Cinzel, Prata, Bodoni Moda, Nunito, Source Sans,
  PT Sans, Arimo. Inget fel på dem, men ett mindre väntat val (Space Grotesk, Unbounded, Bricolage Grotesque,
  Instrument Serif, Archivo, Familjen Grotesk …) ger ofta mer karaktär.
- **Slitna par:** Fraunces + JetBrains Mono, Inter + vad som helst, Playfair + Lato.
- **Värt att ifrågasätta:** gradienttext, cyan-på-mörkt, ren `#000`/`#fff`, identiska kortrutnät, accentlist i vänsterkanten,
  allt centrerat med samma vikt.
- **Viktkontrast:** dramatisk (300 mot 900) läser bättre i rörelse än 400 mot 700.
- **Storlekar för video (riktvärden):** rubriker 60 px+, brödtext 20 px+, etiketter 16 px+; `tabular-nums` på siffror.
- **Tempo (riktvärden):** 1–3 ord ≈ 2–3 s, 4–10 ord ≈ 3–4 s, 11–20 ord ≈ 4–6 s; sista läsbara elementet klart vid ungefär halva scenen.
- **Övergångar:** guiden menar att de flesta klipp bör vara hårda klipp och att shaders passar bäst på 2–3 nyckelmoment.
  Det är en bra default, men en filmisk titel (mall D) har shader på varje skarv och det funkar.

## Tekniska render-regler (de enda hårda kraven)

- **Determinism:** inget `Math.random()` (använd seedad PRNG), inget `Date.now()`, `setTimeout`, `requestAnimationFrame` eller
  `stagger: { from: "random" }`. `repeat: -1` kräver en ändlig `data-duration` på roten.
- **Media:** ramverket spelar media (`video.play()` används aldrig). Ljud på `<audio>`, stum b-roll `muted`, inga base64-mediafiler.
- **Shader-kedjan:** en `HyperShader.init()` per komposition med en *sammanhängande* ankarlista
  (`scenes.length === transitions.length + 1`). Första ankaret visas med `tl.set("#sN", { opacity: 1 }, start)`. Ankarscener
  får inga andra `tl.set`/`tl.to` på själva containern. Ingen exit-tween före en shader (shadern *är* exiten).
- **Skillnad mot guiden (HyperFrames 0.8.x):** guiden lägger `autoAlpha`-växlar på icke-ankarscener. Lint stoppar nu det
  (`gsap_animates_clip_element`), och ramverket visar/döljer `.clip`-scener självt via `data-start`/`data-duration`. Mallarna
  här har därför inga sådana växlar. Guidens mall B hade ankarkedjan `[s4,s5,s7,s8]`, vilket ger en s5→s7-shader ovanpå s6.
  Mallen här använder en sammanhängande kedja `[s4..s8]` med en kort crossfade s6→s7.
- **Lint:** `npx hyperframes lint` ska ge 0 fel. Varningarna `nested_structure_needs_subcomposition` och
  `timeline_track_too_dense` är förväntade för enfilsmallar med HyperShader.

> Källa: HyperFrames (HeyGen), Apache-2.0: `docs/guides/claude-design-hyperframes.md` och `claude-design-send-to-hyperframes.md`.
> Bearbetad och översatt 2026-10-08.
