#!/usr/bin/env python
"""
make-free-sfx.py — fyll sfx/ med en GRATIS ljudpalett under exakt de namn som mix-sfx.sh och
reference/sound-design.md använder (whoosh, pop, click, riser, swell, highlighter …).

Lagt till vid importen till content-engine: kitets originalpalett (CreatingWithJerry, betald)
och bed-låten fick inte följa med. Det här är standardvägen — gratis, lokalt, ingen nyckel:

  1. HyperFrames SFX-bibliotek (Pixabay Content License — fritt även kommersiellt), om det finns:
       $HF_SFX_DIR, ~/.claude/skills/media-use/audio/assets/sfx,
       ~/video-tools/hyperframes/skills/media-use/audio/assets/sfx
  2. Allt som saknas där syntetiseras här (Python stdlib, ingen numpy) — eget material.

    python library/kits/nextphase/skills/nextphase-short-editing/scripts/make-free-sfx.py
    python …/make-free-sfx.py --synth-only        # bara syntes, inga Pixabay-filer
    python …/make-free-sfx.py --force             # skriv över befintliga filer

Betalt alternativ (valfritt): scripts/gen-sfx.sh (ElevenLabs, kräver API-nyckel, kostar krediter).
Skriver sfx/SOURCES.txt med källan för varje fil.
"""
from __future__ import annotations

import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse
import math
import os
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path

SR = 48000
SFX = Path(__file__).resolve().parent.parent / "sfx"

# palette name -> (HyperFrames file, ffmpeg trim args or None)
# (whoosh-short/click-soft are byte-identical to whoosh/click in the HF set, so whoosh-2 and
#  futuristic-click are synthesized to keep the palette varied)
HF_MAP = {
    "whoosh": ("whoosh.mp3", None),
    "pop": ("pop.mp3", None),
    "click": ("click.mp3", None),
    "magic-reveal": ("sparkle.mp3", None),
    "riser": ("riser.mp3", ["-ss", "0.9", "-t", "2.6"]),  # Pixabay riser builds 0.9s→~3.3s, then cuts off
    "confirm": ("chime.mp3", None),
    "ping": ("ping.mp3", None),
    "keyboard": ("typing.mp3", None),
}
ALL = ["whoosh", "whoosh-2", "swoosh", "pop", "click", "futuristic-click", "magic-reveal", "riser",
       "camera-shutter", "swell", "highlighter", "confirm", "ping", "beep", "keyboard", "vinyl-rewind"]


def hf_dir(arg: str | None) -> Path | None:
    home = Path.home()
    for c in [arg, os.environ.get("HF_SFX_DIR"),
              home / ".claude/skills/media-use/audio/assets/sfx",
              home / "video-tools/hyperframes/skills/media-use/audio/assets/sfx"]:
        if c and Path(c).is_dir() and (Path(c) / "whoosh.mp3").exists():
            return Path(c)
    return None


# ------------------------------------------------------------------ synthesis (stdlib only)
def noise() -> float:
    return random.uniform(-1.0, 1.0)


def onepole(samples: list[float], cutoff: float, high: bool = False) -> list[float]:
    a = math.exp(-2 * math.pi * cutoff / SR)
    out, y = [], 0.0
    for x in samples:
        y = (1 - a) * x + a * y
        out.append(x - y if high else y)
    return out


def norm(samples: list[float], peak: float = 0.7) -> list[float]:
    m = max(1e-9, max(abs(s) for s in samples))
    return [s * peak / m for s in samples]


def env_bell(t: float, d: float, power: float = 2.0) -> float:
    return math.sin(math.pi * min(max(t / d, 0), 1)) ** power


def synth(name: str) -> list[float]:
    random.seed(hash(name) & 0xFFFF)
    def gen(d, f):
        return [f(i / SR) for i in range(int(d * SR))]
    if name in ("whoosh", "whoosh-2", "swoosh"):
        d = {"whoosh": 0.75, "whoosh-2": 0.5, "swoosh": 0.42}[name]
        s = gen(d, lambda t: noise() * env_bell(t, d, 3))
        s = onepole(onepole(s, 2600), 180, high=True)
        return norm(s, 0.75)
    if name == "pop":
        return norm(gen(0.16, lambda t: math.sin(2 * math.pi * (950 * t - 2600 * t * t)) * math.exp(-t * 32)), 0.7)
    if name == "click":
        return norm(onepole(gen(0.05, lambda t: noise() * math.exp(-t * 420)), 900, high=True), 0.7)
    if name == "futuristic-click":
        return norm(gen(0.14, lambda t: 0.6 * math.sin(2 * math.pi * 2400 * t) * math.exp(-t * 55)
                        + 0.4 * noise() * math.exp(-t * 500)), 0.6)
    if name == "magic-reveal":
        notes = [(1046.5, 0.0), (1318.5, 0.11), (1568.0, 0.22), (2093.0, 0.33), (2637.0, 0.44)]
        def f(t):
            v = 0.0
            for hz, st in notes:
                if t >= st:
                    v += 0.25 * math.sin(2 * math.pi * hz * (t - st)) * math.exp(-(t - st) * 3.2)
            return v + 0.05 * noise() * math.exp(-t * 2)
        return norm(gen(1.8, f), 0.6)
    if name == "riser":
        d = 2.5
        s = gen(d, lambda t: (0.55 * noise() + 0.35 * math.sin(2 * math.pi * (180 * t + 170 * t * t))) * (t / d) ** 2.2)
        return norm(onepole(s, 4500), 0.75)
    if name == "swell":
        d = 0.75
        s = gen(d, lambda t: noise() * ((t / 0.5) ** 2 if t < 0.5 else math.exp(-(t - 0.5) * 14)))
        return norm(onepole(onepole(s, 1800), 120, high=True), 0.6)
    if name == "camera-shutter":
        s = gen(0.22, lambda t: noise() * (math.exp(-t * 110) + (0.8 * math.exp(-(t - 0.075) * 90) if t >= 0.075 else 0)))
        return norm(onepole(s, 1600, high=True), 0.7)
    if name == "highlighter":
        d = 0.5
        s = gen(d, lambda t: noise() * (0.55 + 0.45 * math.sin(2 * math.pi * 36 * t)) * env_bell(t, d, 0.6))
        return norm(onepole(onepole(s, 5200), 1400, high=True), 0.5)
    if name == "confirm":
        return norm(gen(0.9, lambda t: 0.45 * math.sin(2 * math.pi * 880 * t) * math.exp(-t * 6)
                        + (0.45 * math.sin(2 * math.pi * 1318.5 * (t - 0.1)) * math.exp(-(t - 0.1) * 6) if t >= 0.1 else 0)), 0.6)
    if name == "ping":
        return norm(gen(0.7, lambda t: math.sin(2 * math.pi * 1760 * t) * math.exp(-t * 7)
                        + 0.3 * math.sin(2 * math.pi * 3520 * t) * math.exp(-t * 12)), 0.6)
    if name == "beep":
        return norm(gen(0.14, lambda t: math.sin(2 * math.pi * 1320 * t) * min(1, t / 0.005) * min(1, (0.14 - t) / 0.03)), 0.55)
    if name == "keyboard":
        hits = sorted(random.uniform(0, 1.15) for _ in range(11))
        def f(t):
            return sum(noise() * math.exp(-(t - h) * 380) for h in hits if 0 <= t - h < 0.03)
        return norm(onepole(gen(1.25, f), 700, high=True), 0.6)
    if name == "vinyl-rewind":
        d = 0.7
        return norm(gen(d, lambda t: (0.6 * math.sin(2 * math.pi * (700 * t - 420 * t * t)) + 0.25 * noise())
                        * (0.6 + 0.4 * math.sin(2 * math.pi * 22 * t)) * env_bell(t, d, 1)), 0.6)
    raise SystemExit(f"okänt ljud: {name}")


def write_wav(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32767)
            frames += struct.pack("<hh", v, v)
        w.writeframes(bytes(frames))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synth-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--hf-dir")
    ap.add_argument("--out", default=str(SFX))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    src = None if a.synth_only else hf_dir(a.hf_dir)
    log = []
    for name in ALL:
        existing = [p for p in out.glob(f"{name}.*") if p.suffix in (".mp3", ".wav", ".aif", ".aiff")]
        if existing and not a.force:
            log.append(f"{name}: behölls ({existing[0].name})")
            continue
        for p in existing:
            p.unlink()
        if src and name in HF_MAP:
            fname, trim = HF_MAP[name]
            dst = out / f"{name}.mp3"
            if trim:
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *trim,
                                "-i", str(src / fname), "-af", "afade=t=out:st=2.45:d=0.15", str(dst)], check=True)
            else:
                shutil.copy2(src / fname, dst)
            log.append(f"{name}: HyperFrames/Pixabay {fname}" + (" (0,9–3,5 s, crest i slutet)" if trim else ""))
        else:
            write_wav(out / f"{name}.wav", synth(name))
            log.append(f"{name}: syntetiserad (make-free-sfx.py)")
    (out / "SOURCES.txt").write_text(
        "Gratis palett skapad av scripts/make-free-sfx.py\n"
        "Pixabay-filer: Pixabay Content License (fri användning, även kommersiellt).\n"
        "Syntetiserade filer: eget material.\n\n" + "\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
