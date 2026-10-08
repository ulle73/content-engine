# Laddring → reveal

7 s: en tunn progressring ritas 0→100 % med räknare, detonerar och 'READY.' stämplas in.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
7-second 1920x1080 video, black background. A thin white progress ring draws from 0° to 360° over 4s while a percentage counter (0→100) ticks in the center in mono type, matching the arc exactly. Ring and counter fade out fully by 4.2s; at 4.2s the ring bursts outward into short radial dashes and "READY." stamps into the center, then holds with a subtle ambient idle (slow breathing scale). No audio. **Spectacle beat:** The ring's completion at 100% detonates — it flashes white, expands past frame, and the reveal rides that expansion out.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/hyperframes` (routern väljer arbetsflöde) – eller ange ett, t.ex. `/motion-graphics`.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Loader → reveal) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
