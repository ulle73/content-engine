# Taktgrid ur musiken + syntetiserade ljudeffekter

**Vad:** `beat_grid.py` mäter musiken (taktslag, ettor/downbeats, starka träffar, "droppen") och
skriver JSON som bilden byggs mot. `sfx_synth.py` syntetiserar ljudeffekter (whoosh, swish, tick,
click, pop, impact, riser, chime, sparkle) och mixar dem från en cue-lista så att varje ljuds
**uppmätta topp** landar på rätt tid. Allt lokalt och gratis – inga ljudfiler att licensiera.
**När:** allt som ska klippas på takt – reels, lyrikvideor, UI-morphs, annonser med musik.

Kör med bibliotekets venv (numpy finns där): `library\.venv\Scripts\python.exe`.
`librosa` används automatiskt om det är installerat, annars en numpy-reserv (spectral flux +
autokorrelation + dynamisk programmering).

```bash
python library/prompts/motion-studio-playbook/beat_grid.py song.wav --fps 30 --out work/prompts/x/beats.json
python library/prompts/motion-studio-playbook/sfx_synth.py mix work/prompts/x/cues.json work/prompts/x/sfx.wav --duration 15 --bed song.wav --bed-gain 0.6
ffmpeg -i work/prompts/x/sfx.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 work/prompts/x/audio.wav
ffmpeg -i picture.mp4 -i work/prompts/x/audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest final.mp4
```

`beats.json`: `{bpm, beats[], downbeats[], beat_frames[], hits[{t, strength, band}], drop}`.
`beat_frames` kan läggas direkt i Motion Engines `BeatMap` (`engine/motion/schema.py`).

## Prompt

```text
Sound and picture share one timeline.
1. Run beat_grid.py on the track. Start the film on a downbeat. If there is a drop, place the key
   visual moment (logo lock-up, product assembled) exactly on it – move the song start if needed.
2. Every scene change lands on a beat; every important arrival lands on a beat or a hit.
3. While building, append a cue for every visual event to cues.json: {"sfx", "t", "gain"} –
   whoosh/swish for fast moves, click/tick for UI and counters, pop for small arrivals,
   impact for big landings, riser into the drop, chime for the CTA. Not every event needs sound.
4. Mix with sfx_synth.py (it aligns each sound's peak 20 ms before t), loudnorm to -14 LUFS, mux.
5. Check: a strip of frames around three hits (review.py strip) – the visual peak and the sound
   peak must coincide. The film must also work muted.
```

## Tips

- Lita inte blint på ett automatiskt grid: lyssna på 2–3 punkter och flytta offset vid behov.
- Musik: egen genererad bädd (Motion Engine `bed`/`pulse`, ACE-Step i `video-tools/ACE-Step-1.5`)
  eller spår med licens som tillåter kommersiellt bruk.
