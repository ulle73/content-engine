# Kinetisk promo från stämningsbrief

15 s 1:1 utan eget spår – musik genereras från en stämningsbeskrivning, typografi i takt.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/music-to-video 15-second 1080x1080 kinetic promo. No track supplied — generate one: driving synthwave, high energy. Cut hard on the beat: full-frame word cards ("FASTER", "SHARPER", "SHIP IT") slam in on downbeats, alternating black/white with inverted type, a glitch flash on each phrase change. End on the wordmark "NOVA" holding with a subtle ambient idle. No TTS.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/music-to-video` (installerad globalt i `~/.claude/skills/music-to-video/`)
- Kräver ev. betald tjänst: api:bild/musikgenerering. Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/music-and-slideshows> (avsnitt: Kinetic promo from a mood brief (no track)) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
