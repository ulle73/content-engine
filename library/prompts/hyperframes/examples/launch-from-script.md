# Lansering från eget manus

~20 s lanseringsvideo från inklistrat manus, utan skärminspelning.

**När:** använd som startpunkt; klistra först in [_preamble.md](_preamble.md) (rörelsegrammatiken), sedan prompten.

## Prompt (original, ordagrann)

```text
/product-launch-video Make a ~20-second 1920x1080 launch video from this script — use it verbatim: "Your CRM is three hours of busywork a day. AutoCRM logs every call, email, and meeting for you. 200 teams already switched. Try it free at autocrmhq.com." No site to capture — invent clean product-y visuals from the script. Male TTS voice, calm and confident; subtle BGM under -18dB.
```

## Anpassa

- Byt all text på skärmen (rubriker, siffror, namn) – skriv gärna svensk copy; låt själva prompten vara på engelska.
- Byt färger/typsnitt mot ditt varumärke (eller peka på en designspec, se brand-from-frame-md).
- Justera längd och format (t.ex. 1080x1920 för Reels/TikTok, 1080x1350 för Instagram-flöde).
- Behåll **Spectacle beat**-meningen om den finns – det är den som bär det överdrivna ögonblicket.

## Kör

- Skill: `/product-launch-video` (installerad globalt i `~/.claude/skills/product-launch-video/`)
- Kräver ev. betald tjänst: api:tts (valfritt – gratis lokal TTS via npx hyperframes tts). Gratisväg: egen ljudfil/bild, lokal TTS eller ACE-Step för musik.

> Källa: <https://hyperframes.heygen.com/prompting/product-launch> (avsnitt: Pasted script, no capture) · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07.
