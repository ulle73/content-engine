# Bar chart race

10 s: fem staplar växer, kör om varandra två gånger, värden räknar upp, ledaren pulserar.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
10-second 1920x1080 video, dark slate background. Title "Top languages 2026" top-left. Five horizontal bars (Python, TypeScript, Rust, Go, Java) grow from zero with staggered starts, overtaking each other twice mid-animation; each bar has a right-edge value label counting up to its final %. End state holds 2s with the leader pulsing once. Hand-draw everything — no chart library. No audio. **Spectacle beat:** The leader's single end pulse is the moment — a +16px overshoot and a bright cap flare, returning to rest exactly on the last frame.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Bar chart race) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
