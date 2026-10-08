"""Synthesised sound effects (numpy only, nothing to license) and a cue-based mixer.

    python sfx_synth.py list
    python sfx_synth.py one whoosh out/whoosh.wav
    python sfx_synth.py mix cues.json out/sfx.wav --duration 15 [--bed bed.wav --bed-gain 0.5]

cues.json: [{"sfx": "pop", "t": 1.20, "gain": 0.6}, {"sfx": "whoosh", "t": 2.0, "dur": 0.5}, ...]
Each cue is placed so the sound's measured PEAK lands 20 ms before `t` (sound slightly early reads
as in sync, late reads as broken). Loudness: run ffmpeg loudnorm afterwards, e.g.
    ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 out.wav
"""

from __future__ import annotations

import argparse
import json
import subprocess
import wave

import numpy as np

SR = 48000
RNG = np.random.default_rng(7)  # fixed seed: same file every run


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def _env(n: int, attack: float = 0.005, decay: float = 6.0) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-decay * t)


def _noise(n: int) -> np.ndarray:
    return RNG.standard_normal(n)


def _sweep_bandpass(x: np.ndarray, f_lo: float, f_hi: float) -> np.ndarray:
    """Cheap time-varying one-pole band-pass: the centre moves f_lo -> f_hi -> f_lo (whoosh shape)."""
    n = len(x)
    shape = np.sin(np.linspace(0, np.pi, n))
    f = f_lo + (f_hi - f_lo) * shape
    a = 1 - np.exp(-2 * np.pi * f / SR)
    lp = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc)
        lp[i] = acc
    return np.diff(lp, prepend=0) * 4


def whoosh(dur: float = 0.5) -> np.ndarray:
    n = int(dur * SR)
    return _sweep_bandpass(_noise(n), 300, 3000) * np.sin(np.linspace(0, np.pi, n)) ** 2


def swish(dur: float = 0.25) -> np.ndarray:
    n = int(dur * SR)
    return _sweep_bandpass(_noise(n), 1200, 6000) * np.sin(np.linspace(0, np.pi, n)) ** 3


def tick(dur: float = 0.03) -> np.ndarray:
    t = _t(dur)
    return np.sin(2 * np.pi * 2600 * t) * (1 - t / dur) * 0.6


def click(dur: float = 0.04) -> np.ndarray:
    t = _t(dur)
    return (np.sin(2 * np.pi * 1800 * t) * 0.5 + _noise(len(t)) * 0.3) * np.exp(-90 * t)


def pop(dur: float = 0.14) -> np.ndarray:
    t = _t(dur)
    freq = 900 - 600 * t / dur
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(len(t), 0.003, 25) * 0.8


def impact(dur: float = 0.45) -> np.ndarray:
    t = _t(dur)
    freq = 45 + 110 * np.exp(-t * 30)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 9)
    crack = _noise(len(t)) * np.exp(-t * 60) * 0.35
    return (body + crack) * 0.9


def riser(dur: float = 1.2) -> np.ndarray:
    t = _t(dur)
    freq = 200 + 1800 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR) * 0.25
    air = _sweep_bandpass(_noise(len(t)), 400, 5000) * 0.5
    return (tone + air) * (t / dur) ** 1.5


def chime(dur: float = 1.2) -> np.ndarray:
    t = _t(dur)
    notes = [1046.5, 1318.5, 1568.0]
    out = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * (3 + k)) for k, f in enumerate(notes))
    return out * np.minimum(1, t / 0.004) * 0.3


def sparkle(dur: float = 0.9) -> np.ndarray:
    t = _t(dur)
    out = np.zeros_like(t)
    for k, f in enumerate([2093, 2637, 3136, 4186]):
        start = k * 0.07
        m = t >= start
        out[m] += np.sin(2 * np.pi * f * (t[m] - start)) * np.exp(-(t[m] - start) * 7)
    return out * 0.2


SFX = {"whoosh": whoosh, "swish": swish, "tick": tick, "click": click, "pop": pop,
       "impact": impact, "riser": riser, "chime": chime, "sparkle": sparkle}


def render(name: str, dur: float | None = None) -> np.ndarray:
    fn = SFX[name]
    x = fn(dur) if dur else fn()
    return x / (np.abs(x).max() + 1e-9) * 0.9


def write_wav(path: str, x: np.ndarray) -> None:
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def read_audio(path: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(float)


def mix(cues: list[dict], duration: float, bed: str = "", bed_gain: float = 0.5, lead: float = 0.02) -> np.ndarray:
    out = np.zeros((int(duration * SR), 2))
    if bed:
        b = read_audio(bed)[: len(out)] * bed_gain
        out[: len(b)] += b
    for cue in cues:
        x = render(cue["sfx"], cue.get("dur")) * cue.get("gain", 0.5)
        peak = int(np.argmax(np.abs(x)))
        start = int((cue["t"] - lead) * SR) - peak
        pan = cue.get("pan", 0.0)
        gains = (min(1, 1 - pan), min(1, 1 + pan))
        lo, hi = max(0, start), min(len(out), start + len(x))
        if hi > lo:
            seg = x[lo - start: hi - start]
            out[lo:hi, 0] += seg * gains[0]
            out[lo:hi, 1] += seg * gains[1]
    peak = np.abs(out).max()
    return out / peak * 0.89 if peak > 0.89 else out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    one = sub.add_parser("one"); one.add_argument("name", choices=sorted(SFX)); one.add_argument("out"); one.add_argument("--dur", type=float)
    m = sub.add_parser("mix"); m.add_argument("cues"); m.add_argument("out"); m.add_argument("--duration", type=float, required=True)
    m.add_argument("--bed", default=""); m.add_argument("--bed-gain", type=float, default=0.5)
    args = ap.parse_args()
    if args.cmd == "list":
        print(" ".join(sorted(SFX)))
    elif args.cmd == "one":
        write_wav(args.out, render(args.name, args.dur))
        print("wrote", args.out)
    else:
        cues = json.load(open(args.cues, encoding="utf-8"))
        write_wav(args.out, mix(cues, args.duration, args.bed, args.bed_gain))
        print(f"wrote {args.out} ({len(cues)} cues)")


if __name__ == "__main__":
    main()
