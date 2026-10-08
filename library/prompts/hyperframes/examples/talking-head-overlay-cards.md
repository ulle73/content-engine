# Talking head med grafikkort

Paketerar ett intervjuklipp med designade overlay-kort (titlar, lower thirds, datacallouts) synkade till transkriptet.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/talking-head-recut Package ./founder-clip.mp4 with designed graphic overlay cards synced to the transcript. 9:16 portrait, warm-paper style. Open with a fullscreen kicker + title hook, drop a lower-third when she names the company, a data callout card counting up the "200+ teams / $1.2M ARR" stat, and a pull-quote card for the strongest line. Speaker stays full-bleed under the cards; shrink her into a corner PiP while the data card holds. The clip plays untouched underneath.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/talking-head-recut` (installerad globalt i `~/.claude/skills/talking-head-recut/`)

> Källa: <https://hyperframes.heygen.com/prompting/captions-and-talking-heads> (avsnitt: Base prompt — overlay cards) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
