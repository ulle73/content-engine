# Lyrikvideo

30 s 9:16 lyrikvideo från en låt, text synkad till sången.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/music-to-video 30-second 1080x1920 lyric video from ./song.mp3 (pick the strongest 30-second section — a verse into the hook). Transcribe the vocals for word timing. Lines rise in one at a time on the beat, big condensed type on a dark grain background; the hook lands with each word punching in on its downbeat. Keyword in each line highlighted in acid green. No photos — typography only. No TTS.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/music-to-video` (installerad globalt i `~/.claude/skills/music-to-video/`)

> Källa: <https://hyperframes.heygen.com/prompting/music-and-slideshows> (avsnitt: Lyric video) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
