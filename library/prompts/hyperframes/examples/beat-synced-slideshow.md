# Beatsynkat bildspel

20 s 1:1: genererade bilder klipps på musikens beatgrid, punch-in på downbeats, whip-pan vid frasbyten.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/music-to-video 20-second 1080x1080 video. Resolve a dark, driving electronic track and cut to its analyzed beat grid — one image per bar, punch-in on downbeats, whip-pan transitions on phrase changes. Generate the eight images rather than using stock: brutalist concrete details as high-contrast monochrome abstracts, one consistent visual language across all eight, each carrying a single cyan light thread. Chrome: a `PLATE 0N/08` counter. End card "CAST IN PLACE" in condensed caps over a hard-edged opaque scrim, with the sub-line "EIGHT SURFACES · ONE HUNDRED BPM". No TTS. **Spectacle beat:** On the loudest downbeat, one image punches to 1.25× with an RGB channel split that snaps back on the next beat. The other cuts stay clean.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/music-to-video` (installerad globalt i `~/.claude/skills/music-to-video/`)
- Kräver ev. betald tjänst: api:bild/musikgenerering; api:heygen (media resolve). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/examples> (avsnitt: Beat-synced slideshow) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
