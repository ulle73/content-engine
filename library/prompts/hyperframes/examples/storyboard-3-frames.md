# Storyboard i 3 bildrutor

~15 s tyst film planerad som storyboard: båge, beats per ruta och tempo-regel.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
Storyboard a 3-frame, ~15-second, 1920x1080 piece. Silent — no narration, no VO track. Message: "Fernwell gives you back the hours other tools take." Arc: Hook → Substance → Landing. Audience: small-team operators evaluating a new tool. Mood: tense synth pulse resolving to warm.  Direction for every frame: ground color deep navy `#0b1220`, ink color warm off-white `#f4efe6`. Nothing else gets a hue — emphasis is inversion, scale, or density only. Reveals stage on internal timestamps, since the piece is silent and there's no spoken cue. At each frame's t=0 only its first element is on screen. The rest arrive on the timestamps below. Holds stay fully still, no drift or breathing. No purple-blue AI gradients, no bokeh, no browser chrome, no drop-shadow cards, no infinite loops or randomness.  Frame 1 — Hook (0.0–4.0s), type: hook, persuasion: counterexample, beat: recognition + tension, focal: the headline. At 0.0s: bold ink headline "Most tools slow you down." slams in, centered. At 1.5s: a single thin accent dot (ink color, small, low weight) fades in top-right — the motif, planted quietly. Hold from 3.0–4.0s.  Frame 2 — Substance, **the breather** (4.0–10.0s), type: benefit_highlight, persuasion: numbered enumeration, beat: aha, focal: the stat. This is the one deliberately calmer, more static frame in the piece. Everything else develops continuously. This one mostly holds. At 4.0s: the accent dot from frame 1 carries over, now larger, sitting quietly left-of-center. At 5.0s: a big stat "3.2 hrs / week" fades in beside it, no motion after it lands. Static hold 6.0–10.0s.  Frame 3 — Landing (10.0–15.0s), type: cta, persuasion: callback + distillation, beat: resolve + inevitability, focal: the completed motif. At 10.0s: the accent dot from frames 1–2 expands and fills into the full Fernwell wordmark lockup — same motif, now complete, denser and larger. At 12.0s: tagline "Fernwell. Built for flow." stamps in below it. Hold 13.5–15.0s.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/storyboards> (avsnitt: Worked example: a silent 3-frame storyboard) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
