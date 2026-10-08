# HyperFrames-prompter (svenskt index)

Promptmönster och dokumentation från [HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen, Apache-2.0),
kopierat och indexerat för content-engine. Prompterna är på engelska, eftersom agenterna och registret fungerar bäst så.
Texten i filmen kan du skriva på svenska.

## Så använder du det

1. Öppna Claude Code. HyperFrames-skillsen är installerade globalt (`~/.claude/skills/`, se `library/external/hyperframes/SKILLS.md`).
2. Klistra in [examples/_preamble.md](examples/_preamble.md) (rörelsegrammatiken) och sedan en exempelprompt.
3. Byt copy, färger och format. Behåll gärna *Spectacle beat*-meningen.
4. Vill du utgå från en färdig mall? Läs [claude-design-template-first.md](claude-design-template-first.md). Den pekar på de körbara
   skeletten i `library/templates/hyperframes-skeletons/`.

Stilråd i dokumenten (t.ex. "banned fonts") är **tips**, inte regler. Det som verkligen måste följas är de tekniska
render-reglerna (determinism, medieregler, shader-kedjan).

## Exempelprompter

| Exempel | Format | Skill |
|---|---|---|
| [Terminal som skriver + produktreveal](examples/terminal-typing-intro.md) | 16:9 | `/motion-graphics` |
| [Capstone: 60 s promo i en enda kameraåkning](examples/capstone-one-take-promo.md) | 16:9 | `/general-video` |
| [Textning: ren ordagrann (anchor)](examples/captions-anchor-verbatim.md) | any | `/embedded-captions` |
| [Talking head med grafikkort](examples/talking-head-overlay-cards.md) | any | `/talking-head-recut` |
| [Filmisk textning bakom motivet](examples/captions-cinematic-embed.md) | any | `/embedded-captions` |
| [Textning i ljus dagsljusscen](examples/captions-bright-scene.md) | 16:9 | `/embedded-captions` |
| [VFX-textning med tryck](examples/captions-vfx-hype.md) | any | `/embedded-captions` |
| [Intervju som 16:9-datafilm](examples/talking-head-data-recut-16x9.md) | 16:9 | `/talking-head-recut` |
| [Vertikal explainer med highlight-textning](examples/explainer-caption-highlight.md) | 9:16 | `/faceless-explainer` |
| [PR → feature-reveal (30 s)](examples/pr-feature-reveal.md) | 16:9 | `/pr-to-video` |
| [PR → changelog-sammanfattning](examples/pr-changelog-roundup.md) | 16:9 | `/pr-to-video` |
| [PR → buggfix-förklaring](examples/pr-fix-explainer.md) | 16:9 | `/pr-to-video` |
| [PR → refaktor-genomgång](examples/pr-refactor-walkthrough.md) | 16:9 | `/pr-to-video` |
| [Kod som skrivs tecken för tecken](examples/code-typing-reveal.md) | 16:9 | `/motion-graphics` |
| [Kod-diff i färg](examples/code-diff-colored.md) | 16:9 | `/motion-graphics` |
| [Kod med svepande highlight-band](examples/code-highlight-band.md) | 16:9 | `/motion-graphics` |
| [Scrolla kod till en nyckelrad](examples/code-scroll-to-line.md) | 16:9 | `/motion-graphics` |
| [Diagram via registerblock](examples/chart-named-block.md) | 16:9 | `/motion-graphics` |
| [Handritad bar chart race](examples/chart-bar-race-handdrawn.md) | 16:9 | `/motion-graphics` |
| [Siffra som räknar upp (ARR)](examples/stat-count-up.md) | 16:9 | `/motion-graphics` |
| [USA-karta (choropleth)](examples/map-us-choropleth.md) | 16:9 | `/motion-graphics` |
| [Flygrutt på karta](examples/map-flight-route.md) | 16:9 | `/motion-graphics` |
| [Varumärke från designspec (frame.md)](examples/brand-from-frame-md.md) | any | `/hyperframes` |
| [Varumärke från en webbplats](examples/brand-from-website.md) | any | `/hyperframes` |
| [Animerat socialt inlägg (tweet-kort)](examples/animated-social-post.md) | 4:5 | `/motion-graphics` |
| [Kartrutt med glödande båge](examples/map-route.md) | 16:9 | `/motion-graphics` |
| [Logo sting med shader-övergång](examples/logo-sting-shader.md) | 16:9 | `/motion-graphics` |
| [Produktlansering från URL (45 s)](examples/product-launch-from-url.md) | 16:9 | `/product-launch-video` |
| [Explainer från inklistrad text](examples/explainer-from-text.md) | 9:16 | `/faceless-explainer` |
| [Beatsynkat bildspel](examples/beat-synced-slideshow.md) | 1:1 | `/music-to-video` |
| [Kinetiskt citat](examples/kinetic-quote.md) | 16:9 | `/hyperframes` |
| [Nedräkning 3-2-1 → titel](examples/countdown-title-card.md) | 16:9 | `/hyperframes` |
| [Bar chart race](examples/bar-chart-race.md) | 16:9 | `/hyperframes` |
| [Före/efter-delning](examples/before-after-split.md) | 16:9 | `/hyperframes` |
| [Laddring → reveal](examples/loader-reveal.md) | 16:9 | `/hyperframes` |
| [3D-kort i Three.js](examples/3d-cards-threejs.md) | 16:9 | `/hyperframes` |
| [Logga som ritas med SVG-streck](examples/svg-line-draw-logo.md) | 16:9 | `/hyperframes` |
| [Ordbyte i rubrik (split-flap)](examples/word-swap-headline.md) | 16:9 | `/hyperframes` |
| [Dashboard med statistikbrickor](examples/stat-tile-dashboard.md) | 16:9 | `/hyperframes` |
| [Vertikal social hook](examples/vertical-social-hook.md) | 9:16 | `/hyperframes` |
| [Ämnes-explainer 30 s (16:9)](examples/explainer-topic-16x9.md) | 16:9 | `/faceless-explainer` |
| [Listicle (5 saker)](examples/explainer-listicle.md) | 9:16 | `/faceless-explainer` |
| [How-to med diagram](examples/explainer-how-to-diagrams.md) | 16:9 | `/faceless-explainer` |
| [Levande telemetripanel (inget står still)](examples/telemetry-panel-alive.md) | 16:9 | `/hyperframes` |
| [Musikvideo från eget spår](examples/music-video-from-track.md) | 1:1 | `/music-to-video` |
| [Lyrikvideo](examples/lyric-video.md) | 9:16 | `/music-to-video` |
| [Kinetisk promo från stämningsbrief](examples/kinetic-promo-mood-brief.md) | 1:1 | `/music-to-video` |
| [Pitch deck (slideshow)](examples/pitch-deck-slideshow.md) | 16:9 | `/slideshow` |
| [Transparent overlay (Spotify-kort)](examples/overlay-spotify-card.md) | any | `/motion-graphics` |
| [Enkel produktintro (kort prompt)](examples/simple-product-intro.md) | any | `/hyperframes` |
| [Vertikal produktteaser 20 s](examples/product-teaser-9x16.md) | 9:16 | `/product-launch-video` |
| [Lansering från eget manus](examples/launch-from-script.md) | 16:9 | `/product-launch-video` |
| [Lansering från bara varumärkesnamn](examples/launch-from-brand-name.md) | 16:9 | `/product-launch-video` |
| [Sajtvisning (site tour)](examples/site-tour.md) | 16:9 | `/product-launch-video` |
| [Hologramglob (Three.js, full spec)](examples/hologram-globe-threejs.md) | 16:9 | `/hyperframes` |
| [Porta från Remotion](examples/remotion-port.md) | any | `/remotion-to-hyperframes` |
| [Storyboard i 3 bildrutor](examples/storyboard-3-frames.md) | 16:9 | `/hyperframes` |
| [SaaS-explainer med namngivna övergångar](examples/saas-explainer-transitions.md) | any | `/general-video` |
| [Titelkort med variabler](examples/title-card-variables.md) | any | `/hyperframes` |
| [Personlig välkomstvideo](examples/personalized-welcome.md) | any | `/hyperframes` |
| [Dashboard i enhetsmockup](examples/device-mockup-dashboard.md) | 16:9 | `/product-launch-video` |
| [Liquid glass-notiser](examples/liquid-glass-notifications.md) | 16:9 | `/motion-graphics` |
| [Hero som krossas/portal](examples/hero-shatter-portal.md) | 16:9 | `/motion-graphics` |
| [Ordmärke med ambient polish](examples/wordmark-ambient-polish.md) | 16:9 | `/motion-graphics` |
| [Visuell spec: nattlig titelkort](examples/visual-spec-night-title.md) | 16:9 | `/hyperframes` |
| [Visuell spec: frostad kommandopalett](examples/visual-spec-command-palette.md) | 16:9 | `/hyperframes` |
| [Visuell spec: ordet PRECISION](examples/visual-spec-precision-word.md) | 16:9 | `/hyperframes` |

## Promptguiden (Level 1–7, engelska original)

| Sida | Om |
|---|---|
| [Anatomy of a one-shot prompt](docs/prompting/anatomy.md) | Sexdelat promptskelett: route, spec, beats, copy, teknik, negativ. |
| [Audio effects and mixing](docs/prompting/audio-effects.md) | Ljudmix i symptom: ducka musik, rensa röst, nivåer. |
| [Capstone — every technique, one journey](docs/prompting/capstone.md) | Capstone: varje teknik i en 62 s film i en tagning. |
| [Captions and talking-head footage](docs/prompting/captions-and-talking-heads.md) | Textning och grafikkort på talking-head-material. |
| [Caption styles](docs/prompting/captions-catalog.md) | Textningsstilar: ton → namngiven caption-komponent. |
| [Code changes and PRs](docs/prompting/code-and-prs.md) | Kodändringar/PR → explainer-video. |
| [Code animations](docs/prompting/code-blocks.md) | Kodanimationer: skriva, diffa, markera, scrolla, teman. |
| [Color grading and film effects](docs/prompting/color-grading.md) | Färgsättning och filmeffekter i fast pipeline-ordning. |
| [Data and maps](docs/prompting/data-and-maps.md) | Diagram, uppräknande siffror och kartor (regioner, flöden, rutter). |
| [Design systems and brand](docs/prompting/design-systems.md) | Peka på en varumärkeskälla (spec, sajt, Figma) i stället för 'on-brand'. |
| [Editing existing videos](docs/prompting/editing-existing-videos.md) | Redigera som i en NLE: trimma, flytta, retajma, byta. |
| [Verified example prompts](docs/prompting/examples.md) | Verifierade exempelprompter + den delade rörelse-preamblen. |
| [Explainers](docs/prompting/explainers.md) | Ansiktslösa explainers från text/ämne. |
| [When to generate artwork](docs/prompting/generated-artwork.md) | När bild ska genereras vs ritas i kod – hybriden. |
| [Iterating](docs/prompting/iterating.md) | Iterera med små riktade ändringar och absoluta mål. |
| [Media and audio](docs/prompting/media-and-audio.md) | Voiceover, musik, ljudeffekter, captions, frilägg, PiP. |
| [Motion that reads premium](docs/prompting/motion.md) | Åtta regler för rörelse som känns premium (inget står still, kameran agerar …). |
| [Motion graphics](docs/prompting/motion-graphics.md) | Korta designledda motion graphics: kinetisk typ, stat, logo sting. |
| [Music videos and slideshows](docs/prompting/music-and-slideshows.md) | Beatsynkad musikvideo vs navigerbart bildspel. |
| [Overlays and lower thirds](docs/prompting/overlays-and-lower-thirds.md) | Lower thirds och sociala overlays per tonläge. |
| [Prompt Guide](docs/prompting/overview.md) | Promptguidens översikt: setup, de två promptformerna, nivåstegen. |
| [Product launch videos](docs/prompting/product-launch.md) | Produktlanseringsvideor från URL, manus eller brief. |
| [Recreating something you saw](docs/prompting/recreating-references.md) | Återskapa något du sett: transkribera rörelse, iterera, destillera. |
| [Porting from Remotion](docs/prompting/remotion-migration.md) | Porta Remotion-kompositioner till HyperFrames. |
| [Rendering and output](docs/prompting/rendering-and-output.md) | Kvalitetsnivå, format, upplösning, fps, molnrendering. |
| [Rules and anti-patterns](docs/prompting/rules-and-anti-patterns.md) | Tekniska regler (determinism, lint) och friktionsmönster – stilråden är tips, inte spärrar. |
| [Runtimes and 3D](docs/prompting/runtimes-and-3d.md) | GSAP som standard; Three.js, Lottie, shaders när det behövs. |
| [The specification dial](docs/prompting/specification-dial.md) | Specificeringsratten: hur täthet i prompten styr avvikelsen. |
| [Storyboards](docs/prompting/storyboards.md) | Prompta planen (båge, beats, tempo) i stället för scen för scen. |
| [Transitions](docs/prompting/transitions.md) | Energi/stämning → namngivna shader- och CSS-övergångar. |
| [Variables and templating](docs/prompting/variables-and-templating.md) | Variabler/slots och batch-render en video per rad. |
| [VFX and liquid glass](docs/prompting/vfx-and-liquid-glass.md) | Enhetsmockups, liquid glass, shatter/portal, ambient polish. |
| [High-fidelity looks](docs/prompting/visual-specs.md) | Visuella specar som namnger, placerar, färgsätter och tajmar varje element. |
| [Vocabulary that changes output](docs/prompting/vocabulary.md) | Ordlista: adjektiv som skillsen översätter till easing, kamera, övergångar, captions, röster. |

## Guider (arbetsflöden och verktyg, engelska original)

- [Render in 4K](docs/guides/4k-rendering.md)
- [Authentication & API keys](docs/guides/authentication.md)
- [Add an avatar presenter](docs/guides/avatar-presenter.md)
- [Add captions or repackage talking-head footage](docs/guides/captions-and-recuts.md)
- [Choose how to create](docs/guides/choose-creation-path.md)
- [claude-design-hyperframes](docs/guides/claude-design-hyperframes.md)
- [Send to HyperFrames](docs/guides/claude-design-send-to-hyperframes.md)
- [Color grade images and footage](docs/guides/color-grading.md)
- [Deploy a preview and render API](docs/guides/deploy.md)
- [Bring a design into a project](docs/guides/design-tools.md)
- [Finish and share a video](docs/guides/export-and-share.md)
- [Create a faceless explainer](docs/guides/faceless-explainer.md)
- [Share feedback](docs/guides/feedback.md)
- [Figma integration](docs/guides/figma.md)
- [Create a custom video](docs/guides/general-video.md)
- [Animate with GSAP](docs/guides/gsap-animation.md)
- [Render HDR video](docs/guides/hdr.md)
- [HTML in Canvas](docs/guides/html-in-canvas.md)
- [HyperFrames or Remotion?](docs/guides/hyperframes-vs-remotion.md)
- [Create through an AI chat](docs/guides/mcp.md)
- [Work with media](docs/guides/media.md)
- [Apply media effects](docs/guides/media-effects.md)
- [Create a motion graphic](docs/guides/motion-graphics.md)
- [Create a music-driven video](docs/guides/music-to-video.md)
- [open-design-hyperframes](docs/guides/open-design-hyperframes.md)
- [Fix a slow preview or render](docs/guides/performance.md)
- [Install the HyperFrames plugin](docs/guides/plugins.md)
- [Turn a pull request into a video](docs/guides/pr-to-video.md)
- [Create a product or website video](docs/guides/product-launch-video.md)
- [Remove a background](docs/guides/remove-background.md)
- [Render from the command line](docs/guides/rendering.md)
- [Install and update agent skills](docs/guides/skills.md)
- [Create an interactive presentation](docs/guides/slideshow.md)
- [Troubleshooting](docs/guides/troubleshooting.md)
- [Per-pixel effects with data-vfx-chain](docs/guides/vfx-chain.md)
- [Use images and video](docs/guides/video-components.md)
- [Use voice, music, sound, and captions](docs/guides/voice-and-audio.md)
- [Let an agent drive Studio](docs/guides/webmcp.md)

Licens och ursprung: [NOTICE.md](NOTICE.md).
