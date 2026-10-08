# Handritad bar chart race

10 s: fem horisontella staplar växer och kör om varandra, handritat utan diagrambibliotek.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/motion-graphics 10-second 1920x1080 video, dark slate background. Title "Top languages 2026" top-left. Five horizontal bars (Python, TypeScript, Rust, Go, Java) grow from zero with staggered starts, overtaking each other twice mid-animation; each bar has a right-edge value label counting up to its final %. End state holds 2s, alive — the leader pulses once, timed to finish exactly on the last frame, never a frozen tail. Hand-author the marks (no chart library) and make them *look* hand-drawn: wobbly ink strokes, not clean rectangles. Say which two pairs overtake and when, or the reveal will land on a different number of crossings each run. No audio.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/motion-graphics` (installerad globalt i `~/.claude/skills/motion-graphics/`)

> Källa: <https://hyperframes.heygen.com/prompting/data-and-maps> (avsnitt: Charts: name the block, or hand-draw) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
