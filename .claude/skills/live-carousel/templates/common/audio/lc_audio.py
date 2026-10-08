"""lc_audio: loop-exact sound design for live carousels. Needs numpy and ffmpeg, nothing paid.

Everything is synthesized: drums, bass, pad, bounces, whooshes, ticks. Named one-shot effects
("pop", "click", "impact-bass-1" ...) come from the free HyperFrames SFX pack when it is installed
(Pixabay licence, ships with the media-use skill). Otherwise a synthesized stand-in is used, so a
project always renders.

Typical slide:
    bus = Bus(sec + 3)                 # 3 s of headroom so tails can ring past the loop point
    g, _ = groove(bars, 0.8)           # 120 BPM bed, a whole number of bars
    bus.add(g, 0.0)
    place_sample(bus, "pop", 1.0, 0.6) # effect transients land exactly on the event time
    x = master(bus, sec, wrap=True)    # the tail wraps to the start, so the loop is seamless
    write_wav(OUT / "01-hook.wav", x)
"""
import os
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
BPM = 120
BEAT = 60 / BPM
rng = np.random.default_rng(7)
# Sample-peak ceiling for every mix (~ -4.4 dBFS). The AAC encode adds up to ~1.8 dB of inter-sample
# overshoot, and HyperFrames >= 0.8.140 refuses audio whose AAC true peak stays above -1 dBTP
# ("audioPadTrim: AAC true peak remained above -1 dBFS"). The kit's original 0.89 / 0.95 failed there.
PEAK = 0.6

_SFX_DIRS = [
    os.environ.get("LC_SFX_DIR", ""),
    "~/.claude/skills/media-use/audio/assets/sfx",
    "~/.agents/skills/media-use/audio/assets/sfx",
    "~/.codex/skills/media-use/audio/assets/sfx",
    "~/.cursor/skills/media-use/audio/assets/sfx",
]
CACHE = Path.cwd() / ".sfx-cache"


def set_cache(path):
    """Where decoded SFX are cached (default ./.sfx-cache). Call once from make_audio.py."""
    global CACHE
    CACHE = Path(path)


# ---------------------------------------------------------------- io
def write_wav(path, x, sr=SR):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak > PEAK * 1.001:  # ceiling guard (see PEAK): only ever turns a too-hot mix down
        x = x * (PEAK / peak)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def read_audio(path):
    """Any audio file -> float stereo at SR (decoded through ffmpeg)."""
    path = Path(path).expanduser()
    if path.suffix.lower() != ".wav" or not _is_pcm16(path):
        CACHE.mkdir(parents=True, exist_ok=True)
        wav = CACHE / (path.stem + ".decoded.wav")
        if not wav.exists() or wav.stat().st_mtime < path.stat().st_mtime:
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(wav)],
                check=True,
            )
        path = wav
    with wave.open(str(path), "rb") as w:
        ch, n, sr = w.getnchannels(), w.getnframes(), w.getframerate()
        x = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32768
    x = x.reshape(-1, ch)
    if ch == 1:
        x = np.repeat(x, 2, axis=1)
    if sr != SR:
        idx = np.arange(0, len(x) - 1, sr / SR)
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
    return x[:, :2]


def _is_pcm16(path):
    try:
        with wave.open(str(path), "rb") as w:
            return w.getsampwidth() == 2 and w.getframerate() == SR
    except Exception:
        return False


# ---------------------------------------------------------------- dsp (FFT based, zero-phase)
def _filt(x, resp):
    n = len(x)
    N = 1 << int(np.ceil(np.log2(max(2, 2 * n))))
    f = np.fft.rfftfreq(N, 1 / SR)
    H = resp(np.maximum(f, 1e-6))
    X = np.fft.rfft(x, N, axis=0)
    if x.ndim == 2:
        H = H[:, None]
    return np.fft.irfft(X * H, N, axis=0)[:n]


def lp(x, fc, order=2):
    return _filt(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def hp(x, fc, order=2):
    return _filt(x, lambda f: 1 / np.sqrt(1 + (fc / f) ** (2 * order)))


def bp(x, lo, hi, order=2):
    return _filt(x, lambda f: 1 / np.sqrt((1 + (lo / f) ** (2 * order)) * (1 + (f / hi) ** (2 * order))))


def convolve(a, b):
    n = len(a) + len(b) - 1
    N = 1 << int(np.ceil(np.log2(n)))
    return np.fft.irfft(np.fft.rfft(a, N) * np.fft.rfft(b, N), N)[:n]


def T(sec):
    return np.arange(int(sec * SR)) / SR


def stereo(x, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l * 1.414, x * r * 1.414], axis=1)


def make_ir(sec=1.6, damp=3.2, bright=5000):
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], axis=1) * np.exp(-damp * t)[:, None]
    ir = lp(ir, bright)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]
    return ir / np.sqrt(np.sum(ir**2))


IR = make_ir()


def reverb(x, wet=0.25):
    y = np.stack([convolve(x[:, c], IR[:, c])[: len(x)] for c in range(2)], axis=1)
    return x + wet * y


class Bus:
    def __init__(self, sec):
        self.x = np.zeros((int(sec * SR), 2), dtype=np.float64)

    def add(self, sig, t, gain=1.0, pan=0.0, onset=0):
        if sig.ndim == 1:
            sig = stereo(sig, pan)
        i = int(round(t * SR)) - onset
        if i < 0:
            sig = sig[-i:]
            i = 0
        j = min(len(self.x), i + len(sig))
        if j > i:
            self.x[i:j] += sig[: j - i] * gain


# ---------------------------------------------------------------- instruments
def kick(level=1.0, f0=150, f1=44, dec=0.42):
    t = T(dec + 0.1)
    f = f1 + (f0 - f1) * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / dec * 3.2)
    click = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 400) * 0.35
    return np.tanh((body + click) * 1.6) * level


def clap(level=1.0):
    t = T(0.45)
    n = rng.standard_normal(len(t))
    e = np.zeros_like(t)
    for d in (0.0, 0.011, 0.022):
        e += np.where(t >= d, np.exp(-(t - d) * 90), 0)
    e += np.where(t >= 0.03, np.exp(-(t - 0.03) * 13), 0) * 0.5
    x = bp(n, 900, 4200) * e
    return stereo(x * level * 0.9, 0)


def hat(level=1.0, open_=False):
    t = T(0.3 if open_ else 0.08)
    x = hp(rng.standard_normal(len(t)), 7500, 3) * np.exp(-t * (11 if open_ else 70))
    return x * level


def sub(freq, dur, level=1.0):
    t = T(dur)
    env = np.minimum(1, t / 0.008) * np.exp(-t * 1.6) * np.minimum(1, (dur - t) / 0.03).clip(0, 1)
    x = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t)
    return np.tanh(x * 1.3) * env * level


def pad(freqs, dur, level=1.0, cutoff=1400):
    t = T(dur)
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.35, 0.0, 0.4):
            ph = (f * (1 + det / 100) * t + rng.random()) % 1.0
            x += 2 * ph - 1
    x = lp(x / (len(freqs) * 3), cutoff, 2)
    env = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4).clip(0, 1)
    return np.stack([x * env, np.roll(x, 240) * env], axis=1) * level


def boop(freq, level=1.0, dec=0.35):
    """Marimba-ish pitched hit: one per bounce / landing."""
    t = T(dec + 0.2)
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t / dec * 3)
    x += 0.35 * np.sin(2 * np.pi * freq * 4.0 * t) * np.exp(-t * 40)
    x += 0.12 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t * 16)
    x += hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 600) * 0.15
    return x * level


def boing(freq=320, level=1.0, dur=0.55, up=False):
    """Cartoon spring: wobbling pitch around a glide."""
    t = T(dur)
    glide = (1 + 0.6 * t / dur) if up else (1.25 - 0.35 * t / dur)
    f = freq * glide * (1 + 0.09 * np.sin(2 * np.pi * 18 * t) * np.exp(-t * 3))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.exp(-t * 5.5) * np.minimum(1, t / 0.004)
    return x * level


def thump(level=1.0):
    return kick(level, f0=110, f1=55, dec=0.22)


def whoosh(dur=0.45, level=1.0, f_lo=500, f_hi=4000, shape="swell"):
    t = T(dur)
    n = rng.standard_normal(len(t))
    s = t / dur
    env = np.sin(np.pi * s) ** 2 if shape == "swell" else (s**2 if shape == "in" else (1 - s) ** 2)
    out = np.zeros_like(t)
    bands = np.geomspace(f_lo, f_hi, 6)
    for k, fc in enumerate(bands):
        w = np.exp(-((s * (len(bands) - 1) - k) ** 2) / 1.2)
        out += bp(n, fc * 0.7, min(fc * 1.4, SR / 2 - 100)) * w
    return out * env * level


def speed_whoosh(vel, level=1.0):
    """Noise whose loudness and brightness follow a velocity curve (sonified easing)."""
    n = rng.standard_normal(len(vel))
    v = vel / (vel.max() or 1)
    return (bp(n, 300, 1200) * v**1.5 + bp(n, 1200, 5000) * v**3) * level


def tick(level=1.0, f=2400):
    t = T(0.05)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 160) + hp(rng.standard_normal(len(t)), 4000) * np.exp(-t * 500) * 0.4) * level


def clunk(level=1.0):
    t = T(0.25)
    x = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 30) + 0.5 * np.sin(2 * np.pi * 730 * t) * np.exp(-t * 45)
    x += bp(rng.standard_normal(len(t)), 1500, 5000) * np.exp(-t * 120) * 0.6
    return x * level


def scribble(dur=0.3, level=1.0):
    t = T(dur)
    n = rng.standard_normal(len(t))
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 34 * t) ** 2
    return bp(n, 1800, 6500) * am * np.sin(np.pi * t / dur) ** 0.6 * level


def whistle_fall(dur=0.5, level=1.0, f0=1500, f1=420):
    t = T(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.03).clip(0, 1)
    return np.sin(ph) * env * level


def crash(level=1.0):
    t = T(1.6)
    x = hp(rng.standard_normal(len(t)), 3500, 2) * np.exp(-t * 2.6)
    return np.stack([x, hp(rng.standard_normal(len(t)), 3500, 2) * np.exp(-t * 2.6)], axis=1) * level


# A minor pentatonic for bounces
NOTE = {n: 440 * 2 ** (k / 12) for n, k in {"A3": -12, "C4": -9, "D4": -7, "E4": -5, "G4": -2, "A4": 0, "C5": 3, "D5": 5, "E5": 7, "G5": 10, "A5": 12, "C6": 15}.items()}


def groove(bars, intensity=1.0, fill=True):
    """Bouncy groove: kick on 1 & 3 (+ the and-of-3), clap 2 & 4, 16th hats, sub bass, Am9 pad."""
    sec = bars * 4 * BEAT
    g = Bus(sec + 2.0)
    bass_line = [55.0, 55.0, 43.65, 49.0]
    for b in range(bars):
        t0 = b * 4 * BEAT
        for k_at in (0, 2, 2.5):
            g.add(kick(0.95), t0 + k_at * BEAT, 0.9 * intensity)
        for c_at in (1, 3):
            g.add(clap(0.55), t0 + c_at * BEAT, 0.8 * intensity)
        for s16 in range(16):
            acc = 1.0 if s16 % 4 == 2 else 0.45 if s16 % 2 == 0 else 0.28
            g.add(hat(acc), t0 + s16 * BEAT / 4 + (0.012 if s16 % 2 else 0), 0.32 * intensity, pan=0.25)
        for oh in (0.5, 1.5, 2.5, 3.5):
            g.add(hat(0.5, open_=True), t0 + oh * BEAT, 0.2 * intensity, pan=-0.3)
        f = bass_line[b % 4]
        for at, ln, mul in ((0, 0.45, 1), (0.75, 0.2, 2), (1.5, 0.45, 1), (2.5, 0.25, 1), (3.0, 0.4, 2)):
            g.add(stereo(sub(f * mul, ln, 0.85)), t0 + at * BEAT, 0.55 * intensity)
        chord = [220.0, 261.63, 329.63, 392.0, 493.88] if b % 4 in (0, 1) else [174.61, 220.0, 261.63, 329.63, 392.0]
        g.add(pad(chord, 4 * BEAT + 0.2, 1.0, 1600), t0, 0.10 * intensity)
        if fill and b == bars - 1:
            for k in range(4):
                g.add(clap(0.35), t0 + 3.5 * BEAT + k * BEAT / 8, 0.25 * intensity * (0.5 + k * 0.17))
    x = g.x
    tt = np.arange(len(x)) / SR
    duck = 1 - 0.28 * np.exp(-((tt % BEAT) / 0.09))  # gentle pump on every beat
    return x * duck[:, None], sec


def tape_stop(sig, t_start, dur):
    """Resample a stereo signal from t_start with playback rate falling 1 -> 0 over dur."""
    i0 = int(t_start * SR)
    n = int(dur * SR)
    r = 1 - np.arange(n) / n
    pos = i0 + np.cumsum(r)
    seg = np.stack([np.interp(pos, np.arange(len(sig)), sig[:, c]) for c in range(2)], axis=1)
    return seg * np.linspace(1, 0.0, n)[:, None] ** 0.5


def music_bed(path, start, dur, gain=0.5):
    """A bar-aligned slice of a music file (your own track, or a free one) as a slide bed."""
    music = read_audio(path)
    music = music / (np.max(np.abs(music)) or 1)
    seg = music[int(start * SR) : int(start * SR) + int(dur * SR)].copy()
    if len(seg) < int(dur * SR):
        seg = np.concatenate([seg, np.zeros((int(dur * SR) - len(seg), 2))])
    fi, fo = int(0.004 * SR), int(0.02 * SR)
    seg[:fi] *= np.linspace(0, 1, fi)[:, None]
    seg[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return seg * gain


def master(bus, sec, wrap=True, target_peak=PEAK):
    """Fold the tail back into the start (seamless loop), light reverb, glue, soft clip."""
    x = bus.x
    n = int(sec * SR)
    out = x[:n].copy()
    if wrap:
        tail = x[n:]
        m = min(len(tail), n)
        out[:m] += tail[:m]
    out = reverb(out, 0.12)
    rms = np.sqrt(lp(np.mean(out**2, axis=1), 12, 1).clip(1e-9))
    thr = 0.18
    gain = np.where(rms > thr, (thr / rms) ** 0.35, 1.0)
    out *= gain[:, None]
    out = np.tanh(out * 1.25) / np.tanh(1.25)
    out *= target_peak / (np.max(np.abs(out)) or 1)
    return out.astype(np.float32)


def match_loudness(x, rms_db=-17.0):
    """Same loudness on every slide, so swiping never jumps in level (soft ceiling at PEAK)."""
    rms = np.sqrt(np.mean(x**2)) or 1e-9
    x = x * (10 ** (rms_db / 20) / rms)
    return (PEAK * np.tanh(x / PEAK)).astype(np.float32)


# ---------------------------------------------------------------- named one-shot effects
def _synth_sfx(name):
    """Synthesized stand-ins for the HyperFrames SFX pack (used when it is not installed)."""
    if name.startswith("impact-bass"):
        big = name.endswith("2")
        t = T(2.2 if big else 1.4)
        f = 32 + (70 if big else 85) * np.exp(-t * 9)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.8 if big else 3.0))
        rum = lp(rng.standard_normal(len(t)), 180) * np.exp(-t * 2.5) * (0.9 if big else 0.4)
        hit = bp(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t * 60) * 0.5
        return stereo(np.tanh((body + rum + hit) * 1.8))
    if name == "riser":
        t = T(9.0)
        s = t / 9.0
        noise = bp(rng.standard_normal(len(t)), 800, 9000) * s**3
        tone = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (s * 3)) / SR) * s**2 * 0.5
        return stereo(noise + tone)
    if name in ("click", "click-soft", "key-press"):
        soft = name != "click"
        t = T(0.08)
        x = bp(rng.standard_normal(len(t)), 1800 if soft else 2500, 7000) * np.exp(-t * (300 if soft else 500))
        x += np.sin(2 * np.pi * (900 if soft else 1500) * t) * np.exp(-t * 200) * 0.6
        if name == "key-press":
            x += np.sin(2 * np.pi * 210 * t) * np.exp(-t * 90) * 0.8
        return stereo(x * (0.6 if soft else 1.0))
    if name == "pop":
        t = T(0.12)
        f = 260 + 700 * np.exp(-t * 60)
        return stereo(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38) * np.minimum(1, t / 0.002))
    if name in ("chime", "ping", "notification"):
        t = T(1.3)
        notes = {"chime": [(1046.5, 0)], "ping": [(1760.0, 0)], "notification": [(1318.5, 0), (1975.5, 0.12)]}[name]
        x = np.zeros_like(t)
        for f, d in notes:
            tt = np.clip(t - d, 0, None)
            on = (t >= d).astype(float)
            for k, a in ((1, 1.0), (2.76, 0.35), (5.4, 0.12)):
                x += np.sin(2 * np.pi * f * k * tt) * np.exp(-tt * (3 + 2 * k)) * a * on
        return stereo(x * 0.6)
    if name == "sparkle":
        out = np.zeros(int(0.9 * SR))
        for k in range(9):
            f = 2400 + rng.random() * 3600
            t = T(0.3)
            seg = np.sin(2 * np.pi * f * t) * np.exp(-t * 18)
            i = int(k * 0.06 * SR)
            out[i : i + len(seg)] += seg[: len(out) - i] * (1 - k / 12)
        return stereo(out * 0.5)
    if name.startswith("glitch"):
        t = T(0.3)
        sq = np.sign(np.sin(2 * np.pi * (220 + 600 * (np.floor(t * 40) % 3)) * t))
        gate = (np.floor(t * 60) % 2).astype(float)
        return stereo(np.round(sq * gate * 6) / 6 * 0.5)
    if name.startswith("whoosh"):
        return stereo(whoosh(0.6, 1.0, 400, 6000, "swell"))
    if name == "typing":
        out = np.zeros(int(1.2 * SR))
        for k in range(10):
            s = _synth_sfx("key-press")[:, 0]
            i = int((k * 0.11 + rng.random() * 0.03) * SR)
            out[i : i + len(s)] += s[: len(out) - i] * 0.7
        return stereo(out)
    raise KeyError(f"unknown effect '{name}'")


def _find_sfx(name):
    for d in _SFX_DIRS:
        if not d:
            continue
        for ext in (".mp3", ".wav"):
            p = Path(d).expanduser() / f"{name}{ext}"
            if p.exists():
                return p
    return None


_SAMPLES = {}


def load(name):
    """(stereo signal normalised to peak 1, onset index) for a named effect."""
    if name not in _SAMPLES:
        src = _find_sfx(name)
        x = read_audio(src) if src else _synth_sfx(name)
        x = x / (np.max(np.abs(x)) or 1)
        on = int(np.argmax(np.max(np.abs(x), axis=1) > 0.12))  # align the transient to the event time
        _SAMPLES[name] = (x, on)
    return _SAMPLES[name]


def place_sample(bus, name, t, gain=1.0, pan=0.0, rate=1.0, cut=None):
    x, on = load(name)
    if rate != 1.0:
        idx = np.arange(0, len(x) - 1, rate)
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
        on = int(on / rate)
    if cut:
        x = x[: int(cut * SR)].copy()
        x[-int(0.02 * SR) :] *= np.linspace(1, 0, int(0.02 * SR))[:, None]
    if pan:
        x = x * np.array([np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)]) * 1.414
    bus.add(x, t, gain, onset=on)


def report(name, x):
    rms = 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-9)
    print(f"{name}: {len(x) / SR:.2f}s peak {np.max(np.abs(x)):.2f} rms {rms:.1f} dBFS")
