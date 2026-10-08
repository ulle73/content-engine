# Musikvideo från eget spår

20 s 1:1 från egen ljudfil: bästa 20 s väljs, klipp på beatgridet.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/music-to-video 20-second 1080x1080 video from ./track.mp3 (pick the best 20 seconds of the track) and the 8 photos in ./shots/. Cut on the beat grid, one photo per bar, punch-in on downbeats, `whip-pan` transitions on phrase changes. End on the last photo with "SUMMER '26" in condensed caps. No TTS.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/music-to-video` (installerad globalt i `~/.claude/skills/music-to-video/`)
- Registerblock: `npx hyperframes add whip-pan`

> Källa: <https://hyperframes.heygen.com/prompting/music-and-slideshows> (avsnitt: Your first win) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
