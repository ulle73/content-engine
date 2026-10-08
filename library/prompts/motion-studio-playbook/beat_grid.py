"""Beat grid for a music track -> JSON (beats, downbeats, hits, drop, beat_frames).

    python beat_grid.py song.wav --fps 30 --out beats.json

Uses librosa when installed (beat_track + onset_detect); otherwise a numpy-only fallback
(spectral-flux onsets, autocorrelation tempo, dynamic-programming beat tracking).
Audio is decoded with ffmpeg, so any format works. Output times are seconds; `beat_frames`
matches the Motion Engine BeatMap (engine/motion/schema.py) at the given fps.
Needs: numpy (+ ffmpeg on PATH). Optional: librosa.
"""

from __future__ import annotations

import argparse
import json
import subprocess

import numpy as np

SR = 22050
HOP = 512


def load(path: str) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def stft_mag(y: np.ndarray, n_fft: int = 2048) -> np.ndarray:
    pad = np.pad(y, n_fft // 2)
    frames = 1 + (len(pad) - n_fft) // HOP
    idx = np.arange(n_fft)[None, :] + HOP * np.arange(frames)[:, None]
    return np.abs(np.fft.rfft(pad[idx] * np.hanning(n_fft), axis=1)).T  # (bins, frames)


def onset_envelope(mag: np.ndarray) -> np.ndarray:
    logm = np.log1p(10 * mag)
    flux = np.maximum(0, np.diff(logm, axis=1)).sum(axis=0)
    flux = np.concatenate([[0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")  # remove slow trend
    flux = np.maximum(flux, 0)
    return flux / (flux.max() + 1e-9)


def tempo(env: np.ndarray, lo: float = 60, hi: float = 180) -> float:
    fps = SR / HOP
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lags = np.arange(len(ac))
    bpm = 60 * fps / np.maximum(lags, 1)
    weight = np.exp(-0.5 * (np.log2(bpm / 120) / 1.0) ** 2)  # mild prior around 120 BPM
    ok = (bpm >= lo) & (bpm <= hi)
    best = lags[ok][np.argmax((ac * weight)[ok])]
    return float(60 * fps / best)


def track_beats(env: np.ndarray, bpm: float, tightness: float = 100) -> np.ndarray:
    """Ellis-style dynamic programming beat tracker. Returns frame indices."""
    period = (SR / HOP) * 60 / bpm
    score = env.astype(float).copy()
    back = np.full(len(env), -1)
    window = np.arange(-int(2 * period), -int(period / 2))
    penalty = -tightness * np.log(-window / period) ** 2
    for i in range(len(env)):
        prev = i + window
        valid = prev >= 0
        if not valid.any():
            continue
        cand = score[prev[valid]] + penalty[valid]
        j = int(np.argmax(cand))
        score[i] += cand[j]
        back[i] = prev[valid][j]
    tail = np.arange(max(0, len(env) - int(period)), len(env))
    i = int(tail[np.argmax(score[tail])])
    beats = []
    while i >= 0:
        beats.append(i)
        i = back[i]
    return np.array(beats[::-1])


def analyse(path: str, fps: int, hits_n: int) -> dict:
    y = load(path)
    duration = len(y) / SR
    mag = stft_mag(y)
    env = onset_envelope(mag)
    times = np.arange(len(env)) * HOP / SR
    method = "numpy"
    try:
        import librosa  # type: ignore

        bpm, beat_frames = librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP)
        bpm = float(np.atleast_1d(bpm)[0])
        beat_idx = np.asarray(beat_frames)
        method = "librosa"
    except ImportError:
        bpm = tempo(env)
        beat_idx = track_beats(env, bpm)
    beats = times[np.clip(beat_idx, 0, len(times) - 1)]

    # Downbeats: the bar phase (0-3) whose beats carry the most low-band energy.
    freqs = np.fft.rfftfreq(2048, 1 / SR)
    low = mag[freqs < 150].sum(axis=0)
    phase_energy = [low[np.clip(beat_idx[p::4], 0, len(low) - 1)].mean() if len(beat_idx[p::4]) else 0 for p in range(4)]
    phase = int(np.argmax(phase_energy))
    downbeats = beats[phase::4]

    # Hits: strongest onset peaks, labelled by dominant band.
    peaks = [i for i in range(1, len(env) - 1) if env[i] > env[i - 1] and env[i] >= env[i + 1] and env[i] > 0.25]
    peaks = sorted(peaks, key=lambda i: -env[i])[:hits_n]
    bands = {"low": freqs < 150, "mid": (freqs >= 150) & (freqs < 2500), "high": freqs >= 2500}
    hits = []
    for i in sorted(peaks):
        energy = {name: float(mag[mask, i].sum()) for name, mask in bands.items()}
        hits.append({"t": round(float(times[i]), 3), "strength": round(float(env[i]), 3), "band": max(energy, key=energy.get)})

    # Drop: biggest rise in low-band energy between consecutive 2-bar windows, snapped to a downbeat.
    drop = None
    bar = 4 * 60 / bpm
    if len(downbeats) > 2:
        def low_energy(a, b):
            m = (times >= a) & (times < b)
            return float(low[m].mean()) if m.any() else 0.0
        rises = [(low_energy(d, d + 2 * bar) - low_energy(d - 2 * bar, d), d) for d in downbeats[1:]]
        drop = round(float(max(rises)[1]), 3)

    return {
        "source": path,
        "method": method,
        "duration": round(duration, 3),
        "bpm": round(bpm, 2),
        "fps": fps,
        "beats": [round(float(b), 3) for b in beats],
        "downbeats": [round(float(b), 3) for b in downbeats],
        "beat_frames": sorted({int(round(b * fps)) for b in beats}),
        "hits": hits,
        "drop": drop,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--hits", type=int, default=24, help="number of strongest hits to keep")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    result = analyse(args.audio, args.fps, args.hits)
    text = json.dumps(result, indent=1)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text)
    print(f"{result['method']}: {result['bpm']} BPM, {len(result['beats'])} beats, {len(result['hits'])} hits, drop={result['drop']}")
    if not args.out:
        print(text)


if __name__ == "__main__":
    main()
