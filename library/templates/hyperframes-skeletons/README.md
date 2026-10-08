# HyperFrames-skelett (Claude Design, mallen först)

Körbara HyperFrames-projekt från guiden *Claude Design + HyperFrames (Template-First)*, ifyllda med demo-innehåll så att de
renderar direkt. Byt `:root`-tokens, Google Fonts och scenernas innehåll. Arbetsgång och smakråd finns i
`library/prompts/hyperframes/claude-design-template-first.md`.

| Mapp | Format | Längd | Övergångar |
|---|---|---|---|
| `a-social-reel/` | 1080×1920 | 15 s, 6 scener | hårda klipp + cinematic-zoom (s3→s4) |
| `b-launch-teaser/` | 1920×1080 | 25 s, 8 scener | kedja s4–s8: cinematic-zoom, light-leak, crossfade, cross-warp-morph |
| `c-product-explainer/` | 1920×1080 | 45 s, 12 scener | kedja s5–s12: sdf-iris, whip-pan, flash-through-white + 4 crossfades |
| `d-cinematic-title/` | 1920×1080 | 60 s, 7 scener | 6 shaders (cross-warp-morph, thermal-distortion, light-leak) |
| `pattern-gallery/` | 1080×1080 | 33 s | 11 animationsmönster, ett per scen |
| `shader-gallery/` | 1080×1080 | 36 s | alla 14 HyperShader-övergångar |

```bash
cd library/templates/hyperframes-skeletons/a-social-reel
npx hyperframes lint                    # 0 fel; varningar om sub-kompositioner är väntade
npx hyperframes preview                 # Studio
npx hyperframes render --quality draft -o ../../../../work/hyperframes/a.mp4
```

Kopiera alltid mappen till `work/<projekt>/` innan du ändrar. Renderingar ska inte hamna i biblioteket.

**Ändringar mot guiden (HyperFrames 0.8.140):**
1. Guiden lägger `autoAlpha`-växlar på icke-ankarscener. Lint avvisar det nu (`gsap_animates_clip_element`), och ramverket
   visar/döljer `.clip`-scener själv, så växlarna och `visibility:hidden` är borttagna.
2. Guidens skelett B har ankarkedjan `[s4,s5,s7,s8]`, som gav en s5→s7-shader ovanpå s6. Här används en sammanhängande kedja
   `[s4..s8]` med en kort CSS-crossfade (shader utelämnad) s6→s7.
3. Guiden beskriver C och D bara i text. Här är de fullt utbyggda enligt guidens scenrytm.
4. letterSpacing-animationer är ersatta med `scale` (lint `gsap_non_transform_motion`).

Renderingstider (draft, CPU Ryzen AI 7 350 med hårdvaru-GPU): A 15 s → 30 s, B 25 s → 51 s, C 45 s → 95 s, D 60 s → 108 s,
mönstergalleri 33 s → 34 s, shadergalleri 36 s → 58 s.
