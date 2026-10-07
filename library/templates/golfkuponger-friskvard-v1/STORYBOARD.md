---
format: 1080x1080
duration: 30.5s
message: "Din chef kan betala din golf – använd friskvårdsbidraget på Golfkuponger."
arc: Hook-fråga → Svar (5 000 kr) → Vad det täcker → 300+ klubbar → Så köper du → Avslut
audience: Anställda i Sverige som spelar golf och har (eller kan få) friskvårdsbidrag
mode: collaborative
music: none
language: sv
tempo: 165 BPM (detected) — beat 0.3636s; music starts at 4.693s into bgm.wav (a phrase start); frames start on beat multiples (84 beats = 30.545s)
---

# Golfkuponger — "Vill du att din chef ska betala din golf?"

Ingen speakerröst: all text står på skärmen (`onscreen:`), läsbar utan ljud i flödet.
Bakgrundsmusik är egen, genererad lokalt med ACE-Step (`assets/bgm.wav`, 165 BPM, offset 4.693s) och läggs in
som host-ljud — därför `music: none` här. Ljudeffekter monteras av orkestratorn på beat-tider.

## Video direction

- **Palette (frame.md):** grounds `green-deep` / `green` and real course photos under a deep-green
  scrim; `cream` paper only for the portal frame. Gold (`pink` key = #D6A536) is the ONE accent —
  single words, the big figure, 2px gold rules, the emblem. Headlines cream on dark, green on cream.
- **Type:** Playfair Display 500 for every headline (600 for the 5 000 figure), Inter 400 body,
  Inter 600 tracked uppercase labels. Swedish å/ä/ö everywhere — verify glyphs render.
- **Motion grammar:** long-tail `power3` / `expo.out` settles, never bounce or overshoot. Text
  enters with a soft upward settle + blur-to-sharp (premium editorial feel). Reveals land ON THE BEAT
  (beat = 0.3636s) — the times in each Scene line are beat-quantized; keep them.
- **Photo treatment:** full-bleed stills enter slightly oversized and settle to rest in the FRONT
  half of the shot (a decelerating pull-back), then hold — no back-half push or drift.
- **Rhythm / held frames:** Frame 2 (the 5 000 figure) and Frame 6 (the close) are the held reads —
  big content resolves, then stays still. Frame 4 is the fastest (image swaps every 4 beats = 1.455s).
- **Global finish (orchestrator mounts at root, NOT in frames):** very subtle film grain + soft
  vignette over the whole film. Workers must not add their own grain/vignette.
- **Negative list:** no bouncy/elastic eases, no lazy breathing, no slow back-half pans, no
  everything-at-t=0 slideshow, no floating bokeh/particles, no purple/blue AI gradients, no drop
  shadows on UI chips, no invented numbers or logos, no text in the bottom 17% band.

## Frame 1 — Kroken

- scene: Frågan byggs fras för fras på beatet över en mörk, stämningsfull bana; "chef" och "golf?" i guld
- onscreen: "Vill du att din chef ska betala din golf?"
- voiceover: ""
- duration: 4.364s
- poster: 3.6s
- transition_in: cut
- status: animated
- src: compositions/frames/01-kroken.html
- type: hook
- persuasion: Provocative question (curiosity gap)
- beat: curiosity + intrigue
- blueprint: kinetic-type-beats (Adapt)
- asset_candidates: assets/anvnd-friskvrdsbidraget-till-golf.png — mörk, stämningsfull parkbana i gryning, används som svagt synlig bakgrund under scrim
- focal: the headline
- roles: anvnd-friskvrdsbidraget-till-golf = background (dim to ~35% under a green-deep scrim)
- sfx: whoosh-short at 0.0s (soft), click-soft on each phrase beat

Adapt: keep the statement-builds-across-beats signature, but as ONE centered 3-line question that assembles phrase by phrase (per-word staggered reveal → `dynamic-content-sequencing`) instead of full-screen swaps.
Scene 1 (0.000–0.727s): green-deep ground; the photo fades up from black to ~35% and settles from slightly oversized to rest by ~2.2s (front-half pull-back only). "Vill du att" enters centered, upper-middle — soft rise + blur-to-sharp, `power3`.
Scene 2 (0.727–2.182s): "din chef" lands at 0.727s (gold "chef"), "ska betala" at 1.455s, "din golf?" at 2.182s (gold "golf?") — centered 3–4-line stack, Playfair display ~11cqw, ≈75% of frame width.
Scene 3 (2.182–4.364s): the question holds still and reads. At 2.909s one clean specular gold sweep passes through "golf?" (`text-shimmer` registry component, installed at compositions/components/). Nothing else moves.

## Frame 2 — Svaret

- scene: "Det kan hen." → "Med friskvårdsbidraget." → stor siffra räknar upp 0 → 5 000 kr, guldlinje, liten text om att arbetsgivaren bestämmer
- onscreen: "Det kan hen. Med friskvårdsbidraget." / "5 000 kr" / "per år – skattefritt" / "Arbetsgivaren bestämmer beloppet."
- voiceover: ""
- duration: 5.818s
- poster: 5.2s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/02-svaret.html
- type: product_intro
- persuasion: Statistical proof (konkret belopp)
- beat: surprise → aspiration
- blueprint: dataviz-countup (Adapt)
- asset_candidates: assets/experiment-card-v1.png — mörkgrön kortbakgrund med dimmig bana (sajtens priskort), som djup bakom siffran
- focal: the 5 000 kr figure
- roles: experiment-card-v1 = background (full-bleed, cover, dim ~50%, the misty course glows faintly at the bottom)
- sfx: riser building into the landing (ends at 3.636s), impact-bass-1 (soft) when the figure lands at 3.636s, sparkle with the shimmer at 4.364s

Adapt: keep the one-hero-metric count-up signature (`counting-dynamic-scale` value-scaled counter); no chart or ring — a single serif figure is the hero.
Scene 1 (0.000–1.091s): "Det kan hen." enters upper-third left-aligned (headline, cream), soft rise + blur-to-sharp.
Scene 2 (1.091–2.182s): at 1.091s "Med friskvårdsbidraget." lands beneath it ("friskvårdsbidraget" in gold). Two-line block, asymmetric 70/30, upper part of frame.
Scene 3 (2.182–3.636s): at 2.182s the two lines step up and shrink slightly (smooth scale-swap → `scale-swap-transition`) to clear the center; "0 kr" appears center and counts up 0 → 5 000 from 2.182s to 3.636s on an ease-out, the figure growing as it climbs (`counting-dynamic-scale`), Playfair 600 stat-figure, Swedish space format "5 000 kr" (tabular numerals so the width doesn't jitter).
Scene 4 (3.636–4.364s): the figure lands exactly at 3.636s at full size (≈60% of frame width); a 2px gold rule draws out beneath it (width reveal, 3.636–4.0s), then at 4.0s "per år – skattefritt" rises in below the rule (body-large, cream).
Scene 5 (4.364–5.818s): at 4.364s one gold specular sweep passes through "5 000 kr" (`text-shimmer`); at 4.727s the small print "Arbetsgivaren bestämmer beloppet." fades in under the content block (caption-mono, cream ~70%), above the bottom 17% band. Hold still to the end.

## Frame 3 — Vad det täcker

- scene: Fullbild av sajtens hero-skogsbana; rubrik "Använd det på golf" och fyra chips staplas in på beatet: Greenfee · Range · Lektioner · Simulator
- onscreen: "Använd det på golf" / "Greenfee" · "Range" · "Lektioner" · "Simulator"
- voiceover: ""
- duration: 4.364s
- poster: 3.6s
- transition_in: blur-crossfade
- status: animated
- src: compositions/frames/03-vad-det-tacker.html
- type: benefit_highlight
- persuasion: Feature-to-benefit translation
- beat: clarity + ease
- blueprint: grid-card-assemble (Adapt)
- asset_candidates: assets/hero-skogsbana.png — solig svensk skogsbana med tallar och bunkrar (sajtens hero)
- focal: hero-skogsbana (the sunny course — the "this is what you get to do" image)
- roles: hero-skogsbana = background (full-bleed, bright; a green-deep gradient scrim from the top ~45% for the headline only)
- sfx: click-soft on each chip (1.091, 1.455, 1.818, 2.182s)

Adapt: keep the staggered self-assembling list signature, as four pill chips in a 2×2 grid over the photo instead of cards.
Scene 1 (0.000–1.091s): the photo settles from slightly oversized to rest by ~2.0s (front-half pull-back); small gold label "FRISKVÅRDSBIDRAGET GÄLLER" (label, gold) and "Använd det på golf" (headline, cream on the top scrim) enter top-left inside the safe area, soft rise + blur-to-sharp.
Scene 2 (1.091–2.182s): four chips assemble one per beat — Greenfee (1.091), Range (1.455), Lektioner (1.818), Simulator (2.182) — 2×2 grid under the headline; each chip is a solid `green` pill (6px radius or full pill) with cream Inter 600 text and a small gold check mark, entering with a short rise + fade (`dynamic-content-sequencing`), no overshoot.
Scene 3 (2.182–4.364s): hold the full read still; the photo is at rest.

## Frame 4 — 300+ klubbar

- scene: Fyra klubbilder byts på beatet (4 slag var) med namnskylt; "300+" och "golfklubbar i hela Sverige" ligger fast ovanpå
- onscreen: "300+" / "golfklubbar i hela Sverige" / skyltar: "Bro Hof Slott" · "Halmstad GK" · "Falsterbo GK" · "Österåker GK"
- voiceover: ""
- duration: 5.818s
- poster: 3.6s
- transition_in: crossfade
- status: animated
- src: compositions/frames/04-klubbar.html
- type: social_proof
- persuasion: Authority by association (kända banor)
- beat: aspiration + belonging
- blueprint: fixed-anchor-cycle (Adapt)
- asset_candidates: assets/klubb-bro-hof-slott.png — solnedgång över kustbana; assets/klubb-halmstad-gk.png — trädkantad fairway i morgonljus; assets/klubb-falsterbo-gk.png — dimmig soluppgång över links med bunker; assets/klubb-osteraker-gk.png — golfare går på fairway med bag
- focal: the pinned "300+" anchor
- roles: all four club photos = background (full-bleed, cover, each with a green-deep bottom-left scrim), cycled
- sfx: whoosh-short (very soft) on each image swap (1.455, 2.909, 4.364s)

Adapt: keep the PINNED-anchor signature — "300+ / golfklubbar i hela Sverige" enters once and never moves — while the surrounding photo cycles; the cycle is a full-bleed image swap with a club name-tag swap.
Scene 1 (0.000–1.455s): Bro Hof Slott photo full-bleed; "300+" (stat-figure, cream, gold "+") enters top-left at 0.0s and "golfklubbar i hela Sverige" (title-card, cream) at 0.364s, then both lock; name-tag "BRO HOF SLOTT" (label on a green-deep tag with gold left rule) slides in at 0.727s at lower-left, above the bottom 17% band.
Scene 2 (1.455–5.818s): every 4 beats the photo swaps — Halmstad GK (1.455), Falsterbo GK (2.909), Österåker GK (4.364) — each swap a quick (~0.35s) cross-dissolve where the incoming photo settles from 106% to 100% scale (`scale-swap-transition`); the name-tag text swaps in place on the same beat (hard-cut token swap → `discrete-text-sequence`). The 300+ anchor never moves. Österåker holds to the end.

## Frame 5 — Så köper du

- scene: Krämvit grund; rubrik "Köp via din förmånsportal"; fyra vita logokort poppar in i 2×2 på beatet; under: "…eller direkt hos oss."
- onscreen: "Köp via din förmånsportal" / [Benifex] [ePassi] [Söderberg & Partners] [Edenred] / "…eller direkt hos oss på golfkuponger.se"
- voiceover: ""
- duration: 4.364s
- poster: 3.8s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/05-portaler.html
- type: social_proof
- persuasion: Friction reduction (du har redan portalen)
- beat: ease + control
- blueprint: grid-card-assemble (Reproduce)
- asset_candidates: assets/portal-benifex.png — Benifex-logga på vitt; assets/portal-epassi.jpg — ePassi-logga på vitt; assets/portal-soderberg-partners.jpg — Söderberg & Partners-logga på vitt; assets/portal-edenred.jpg — Edenred-logga på vitt
- focal: the 2×2 logo grid
- roles: all four portal logos = supporting (each inside its own white logo-card, native colors, never recolored or cropped)
- sfx: click-soft on each logo card (0.727, 1.091, 1.455, 1.818s)

Scene 1 (0.000–0.727s): cream paper ground; gold-deep label "FRISKVÅRD VIA ARBETSGIVAREN" and headline "Köp via din förmånsportal" (headline, green) enter top-left, soft rise + blur-to-sharp.
Scene 2 (0.727–2.182s): four white logo-cards (8px radius, 2px hairline in green at ~14%) assemble one per beat in a 2×2 grid, center of frame — Benifex (0.727), ePassi (1.091), Söderberg & Partners (1.455), Edenred (1.818) — short rise + fade, `power3`, staggered cascade (`dynamic-content-sequencing`).
Scene 3 (2.182–4.364s): at 2.545s the line "…eller direkt hos oss på golfkuponger.se" rises in under the grid (body, ink; "golfkuponger.se" in green 600). Hold still.

## Frame 6 — Avslut

- scene: Varmt ljus sveper in, guldemblemet blommar fram på djupgrönt, ordmärket under; "Låt chefen bjuda på golfen." och URL:en golfkuponger.se i guld
- onscreen: "Låt chefen bjuda på golfen." / "golfkuponger.se"
- voiceover: ""
- duration: 5.818s
- poster: 4.4s
- transition_in: blur-crossfade
- status: animated
- src: compositions/frames/06-avslut.html
- type: cta
- persuasion: Future pacing
- beat: motivation + urgency-to-act
- blueprint: logo-assemble-lockup (Adapt)
- asset_candidates: assets/golfkuponger-logo.png — guldpräglat GK-emblem; assets/golfkuponger-loggan02-2026-04-10-cropped.png — guldordmärke GOLFKUPONGER.SE på svart
- focal: golfkuponger-logo (the gold emblem)
- roles: golfkuponger-logo = cutout (centered hero, its own dark glow blends into green-deep); golfkuponger-loggan02 = supporting (wordmark under the emblem — its black ground must blend: use mix-blend-mode screen/lighten on green-deep, or crop to the gold glyphs)
- sfx: whoosh-cinematic into the light sweep at 0.0s, chime when the emblem settles at 1.091s, sparkle with the URL shimmer at 3.636s

Adapt: keep the "spring-bloomed whole on a cleared stage → centered lockup → URL end card" signature, without overshoot: the emblem blooms from soft blur + slight scale to rest.
Scene 1 (0.000–1.091s): green-deep ground; a warm, finite light-leak sweeps across from the left (`organic-light-leak-overlay` registry block at compositions/organic-light-leak-overlay.html, low intensity, golden); the gold emblem blooms in at center-upper from blur + 90% scale to sharp 100% (`spring-pop-entrance` in its smooth critically-damped settle), a soft gold glow blooms behind it (`ambient-glow-bloom`), landing at 1.091s.
Scene 2 (1.091–2.182s): at 1.455s the gold wordmark fades up beneath the emblem (supporting, ~55% width).
Scene 3 (2.182–2.909s): at 2.182s "Låt chefen bjuda på golfen." rises in below the lockup (headline, cream, "golfen" in gold).
Scene 4 (2.909–4.9s): at 2.909s "golfkuponger.se" lands as the URL line (title-card, gold) with a 2px gold rule drawing out above it; at 3.636s one specular sweep passes through the URL (`text-shimmer`). Hold still.
Scene 5 (4.9–5.818s): final exit (this is the last frame): everything fades gently to green-deep/black over the last ~0.9s with a slight blur.
