# HyperFrames-skills (installerade globalt)

De här skillsen ligger i användarens globala Claude Code-katalog (`~/.claude/skills/<namn>/SKILL.md`,
på den här maskinen `C:\Users\rydqv\.claude\skills\`). De är **inte** kopierade till repot. Anropa dem i Claude Code
med `/<namn>`. Uppdatera med `npx hyperframes skills update <namn>`.

Börja alltid i `/hyperframes`. Den routar vidare till rätt arbetsflöde.

| Skill | Vad den gör | Fil |
|---|---|---|
| `/hyperframes` | Obligatorisk ingång för all video i HyperFrames: fångar avsikt, väljer arbetsflöde och installerar rätt skill. | `~/.claude/skills/hyperframes/SKILL.md` |
| `/general-video` | Fri/anpassad komposition: längre brand- och sizzle-reels, montage, titelkort, companion-läge. | `~/.claude/skills/general-video/SKILL.md` |
| `/motion-graphics` | Korta designledda motion graphics: kinetisk typ, stat-uppräkning, logo sting, lower thirds, kartor, animerade tweets. | `~/.claude/skills/motion-graphics/SKILL.md` |
| `/product-launch-video` | Produktlansering/promo från URL, manus eller brief – SaaS-promos, feature reveals, site tours. | `~/.claude/skills/product-launch-video/SKILL.md` |
| `/faceless-explainer` | Ansiktslös explainer från text/ämne – visuellt uppfunnet per scen (typografi, diagram, data-viz). | `~/.claude/skills/faceless-explainer/SKILL.md` |
| `/music-to-video` | Beatsynkad video från ett musikspår: lyrikvideo, bildspel eller kinetisk promo. | `~/.claude/skills/music-to-video/SKILL.md` |
| `/pr-to-video` | GitHub-PR → kodändrings-explainer (changelog, feature reveal, fix, refaktor). | `~/.claude/skills/pr-to-video/SKILL.md` |
| `/embedded-captions` | Textning på talking-head: ordagrann rail, filmisk bakom motivet eller VFX-stilar (35 identiteter). | `~/.claude/skills/embedded-captions/SKILL.md` |
| `/talking-head-recut` | Paketera talking-head/intervju med designade grafikkort synkade till transkriptet. | `~/.claude/skills/talking-head-recut/SKILL.md` |
| `/slideshow` | Navigerbar presentation/pitch deck med fragment, förgrening och talarläge. | `~/.claude/skills/slideshow/SKILL.md` |
| `/remotion-to-hyperframes` | Porta Remotion-kompositioner (React) till HyperFrames-HTML. | `~/.claude/skills/remotion-to-hyperframes/SKILL.md` |
| `/figma` | Importera Figma-innehåll (assets, tokens, komponenter, storyboard) till en komposition. | `~/.claude/skills/figma/SKILL.md` |
| `/hyperframes-registry` | Sök, installera och koppla in registerblock/komponenter (~400) – använd innan du handbygger en effekt. | `~/.claude/skills/hyperframes-registry/SKILL.md` |
| `/hyperframes-animation` | All animationskunskap: rörelseregler, scen-blueprints, övergångar, 24 textanimationer, runtime-adaptrar. | `~/.claude/skills/hyperframes-animation/SKILL.md` |
| `/hyperframes-keyframes` | Punch-in, zoom, reframe, Ken Burns, kamerarörelser, masker, SVG-morf – seek-säkra keyframes. | `~/.claude/skills/hyperframes-keyframes/SKILL.md` |
| `/hyperframes-core` | Kompositionskontraktet: data-*-attribut, clips, spår, sub-kompositioner, variabler, determinism. | `~/.claude/skills/hyperframes-core/SKILL.md` |
| `/hyperframes-creative` | Kreativ riktning utan animation: designspec, paletter, typografi, berättarröst, beats, varumärke. | `~/.claude/skills/hyperframes-creative/SKILL.md` |
| `/hyperframes-cli` | CLI-loopen: init, add, catalog, lint, check, snapshot, preview, render, batch, moln/Lambda. | `~/.claude/skills/hyperframes-cli/SKILL.md` |
| `/hyperframes-audio` | Mixa ljud i en komposition: fades, ducking, EQ/kompressor/reverb, automation, submix-grupper. | `~/.claude/skills/hyperframes-audio/SKILL.md` |
| `/hyperframes-studio` | Arbeta med en person i Studio: planera, storyboard, tidslinjelayout och safe zones. | `~/.claude/skills/hyperframes-studio/SKILL.md` |
| `/media-use` | Media-OS: hämta/generera musik, SFX, bild, ikon, logga, röst, LUT; TTS, transkription, frilägg. | `~/.claude/skills/media-use/SKILL.md` |

Relaterat: promptguiden i `library/prompts/hyperframes/`, mallar i `library/templates/hyperframes-skeletons/`,
registerindexet i `LIBRARY.json` här bredvid (`npx hyperframes catalog --query "…"` för att söka).
