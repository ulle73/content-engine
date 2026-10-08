"""Music + sound effects for a photo live carousel: one loop-exact mix per slide in audio/out/<slide>.wav.

Run:  <skill>/scripts/py audio/make_audio.py      (render_all.py runs it for you)
Timing comes from carousel.json -> cues.<slide> (the same numbers the slide's render(t) uses):
  dur    loop length; keep it a whole number of 120 BPM bars (4, 6 or 8 s)
  hits   impacts -> sub boom + crash, with a whoosh leading in
  shine  light sweeps -> a soft sparkle
Music bed: the synthesized 120 BPM groove by default. To use a track you have the rights to, set
carousel.json -> "music": {"file": "path/to/song.mp3", "start": 0.0}. Each slide then plays the next
bar-aligned window of the song, so the music carries on as people swipe. Add slide-specific sounds
in extra() below (a count-up -> ticks, a cursor click -> "click", a pill lighting -> "pop").
"""
import json
from pathlib import Path

import numpy as np

import lc_audio
from lc_audio import *  # noqa: F401,F403

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
lc_audio.set_cache(HERE / ".sfx-cache")
CFG = json.loads((HERE.parent / "carousel.json").read_text(encoding="utf-8-sig"))
CUES = CFG.get("cues", {})
MUSIC = CFG.get("music") or {}


def extra(name, bus, cue):
    """Slide-specific sounds. Example: if name == "02": place_sample(bus, "click", 1.5, 0.6)"""


def slide(name, offset):
    cue = CUES.get(name, {})
    dur = float(cue.get("dur", 6))
    bus = Bus(dur + 3)
    if MUSIC.get("file"):
        bus.add(music_bed(MUSIC["file"], float(MUSIC.get("start", 0)) + offset, dur, 0.6), 0)
    else:
        bars = max(1, int(round(dur / (4 * BEAT))))
        g, _ = groove(bars, 0.75)
        bus.add(g[: int(dur * SR) + int(2 * SR)], 0)
    for i, h in enumerate(cue.get("hits", [])):
        big = i == 0
        bus.add(whoosh(0.45, 0.5 if big else 0.35, 400, 5000, "in"), h - 0.45, 1.0)
        place_sample(bus, "impact-bass-2" if big else "impact-bass-1", h, 0.45 if big else 0.32, cut=1.0)
        bus.add(crash(0.35 if big else 0.2), h, 1.0)
        if big and cue.get("extrude"):
            place_sample(bus, "pop", h + 0.02, 0.4)
    for s0 in cue.get("shine", []):
        place_sample(bus, "sparkle", s0 + 0.05, 0.22, pan=0.3)
    extra(name, bus, cue)
    return match_loudness(master(bus, dur, wrap=True)), dur


if __name__ == "__main__":
    offset = 0.0
    for name in CFG.get("slides", []):
        x, dur = slide(name, offset)
        offset += dur
        write_wav(OUT / f"{name}.wav", x)
        report(name, x)
