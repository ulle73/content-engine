"""Ljud för FAIV-filmen: bara nedräkningens tick-tack och sliderns whoosh (Pixabay Content License).

  ../../.venv/Scripts/python.exe -I audio.py   -> build/mix.wav

Ingen musik – beställaren lägger en riktig låt manuellt. SFX: ~/.claude/skills/media-use/audio/assets/sfx.
Mixkit-filerna (låt + effekter) får inte ligga i mallen – fetch_assets.py hämtar dem.
"""
import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as V  # noqa: E402

SR = 48000
N = int(V.DUR * SR)
HERE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.expanduser("~/.claude/skills/media-use/audio/assets/sfx")


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy()


def sfx(name):
    return load(os.path.join(SFX, name + ".mp3"))


def db(x):
    return 10 ** (np.asarray(x) / 20)


def place(bus, x, at, gain_db=0.0, src_from=0.0, src_to=None, fade_in=0.0, fade_out=0.0):
    """Lägg x (2×n) på bus vid tiden at. src_from/src_to klipper källan, fades i sekunder."""
    a, b = int(src_from * SR), int(src_to * SR) if src_to else x.shape[1]
    seg = x[:, a:b].copy()
    n = seg.shape[1]
    if fade_in:
        k = min(n, int(fade_in * SR))
        seg[:, :k] *= np.linspace(0, 1, k)
    if fade_out:
        k = min(n, int(fade_out * SR))
        seg[:, n - k:] *= np.linspace(1, 0, k)
    i = int(round(at * SR))
    if i < 0:
        seg, i = seg[:, -i:], 0
    m = min(seg.shape[1], N - i)
    if m > 0:
        bus[:, i:i + m] += seg[:, :m] * db(gain_db)


def pan(x, p):
    l, r = np.cos((p + 1) * np.pi / 4) * 1.414, np.sin((p + 1) * np.pi / 4) * 1.414
    return np.stack([x[0] * l, x[1] * r])


# Slider-whooshen är godkänd av beställaren 2026-10-12 och ska låta exakt som i leverans v3:
# whoosh-short, panorering -0,5/0,5/-0,4, 0,18 s efter varje rörelsestart, slutlig nivå -11,0 dB
# (v3: -14 dB i mixen, -1,93 dB peak-normalisering, +4,95 dB loudnorm). Ändra inte.
WHOOSH_GAIN_DB = -11.0
TICK_GAIN_DB = -9.0
TICK_EVERY = 0.5             # klocka: tic … tac … (tic-tac-tic-tac-tic under 2 s)
COUNT_GAIN_DB = -12.0        # räkneverket 0 → 50
COUNT_MIN_GAP = 0.028        # tätare än så smälter klicken ihop till ett surr


def speed(x, k):
    """Spela upp med hastighet k (k > 1 = högre ton och kortare)."""
    idx = np.arange(0, x.shape[1] - 1, k)
    i0 = idx.astype(int)
    fr = idx - i0
    return x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr


def tic_tac():
    """Tic = klicket två halvtoner upp, tac = sex halvtoner ner: tydligt olika som en klocka."""
    c = sfx("click-soft")
    return speed(c, 2 ** (2 / 12))[:, : int(0.10 * SR)], speed(c, 2 ** (-6 / 12))[:, : int(0.16 * SR)]


MIXKIT = os.path.join(HERE, "sfx-mixkit")      # Mixkit Sound Effects Free License, se sfx-mixkit/SOURCES.txt

# Lager per moment: (fil, sekunder efter händelsen, punkten i filen som ska landa där, dB, klipp från, klipp till)
# Punkten är uppmätt ansats/topp (se analysen i sfx-mixkit). Provning: audition.py.
REVEAL = {   # extraljusen slås på (händelse = T_CLICK)
    "H1": [("electric-switch", 0.0, 0.263, -6), ("quick-bass-switch", 0.0, 0.135, -3),
           ("cinematic-whoosh-deep-impact", 0.30, 0.629, -12)],
    "H2": [("quick-bass-switch", 0.0, 0.135, -2), ("cinematic-whoosh-deep-impact", 0.30, 0.629, -11)],
    "H3": [("electric-switch", 0.0, 0.263, -5), ("cinematic-whoosh-deep-impact", 0.30, 0.629, -11)],
    "H4": [("light-switch-sound", 0.0, 0.018, -2), ("quick-bass-switch", 0.0, 0.135, -3)],
    "H5": [("machine-activation-short", -0.1, 0.111, -10, 0.0, 0.9), ("cinematic-whoosh-deep-impact", 0.30, 0.629, -12)],
    "H6": [("electric-switch", 0.0, 0.263, -6), ("shot-light-energy-flowing", 0.35, 1.908, -14, 1.2, 4.0)],
}
SIGHT = {    # siktet låser på rådjuret (händelse = T_DAR; ramen krymper 0,3 s och sätter sig)
    "S1": [("camera-auto-focus", 0.0, 0.10, -16, 0.10, 0.40), ("gear-fast-lock-tap", 0.26, 0.012, -10)],
    "S2": [("gear-fast-lock-tap", 0.26, 0.012, -11)],
    "S3": [("computer-digital-lock", 0.20, 0.033, -14)],
    "S4": [("camera-auto-focus", 0.0, 0.10, -13, 0.10, 0.48)],
    "S5": [("modern-technology-select", 0.26, 0.0, -10)],
    "S6": [("data-scaner", 0.0, 0.112, -18, 0.0, 0.45)],
}
CHOICE = {"reveal": "H1", "sight": "S5"}
SEE_MORE_DB = -6.0           # samma tändljud, svagare, när ljuset slås på igen vid SE MER.


def layers(bus, spec, t_event, extra_db=0.0):
    for lay in spec:
        name, off, align, g = lay[:4]
        src_from, src_to = (lay[4], lay[5]) if len(lay) > 4 else (0.0, None)
        x = load(os.path.join(MIXKIT, name + ".mp3"))
        place(bus, x, t_event + off - (align - src_from), g + extra_db, src_from, src_to,
              fade_out=0.04 if src_to else 0.0)


def build(reveal=None, sight=None):
    a = V
    fx = np.zeros((2, N))
    ts = np.arange(N) / SR
    # --- nedräkningen: tic-tac under båda timrarna (klickets ansats ligger 0,048 s in före hastighetsbyte)
    tic, tac = tic_tac()
    for t0, t1 in (a.TIMER1, a.TIMER2):
        n = int(round((t1 - t0) / TICK_EVERY))
        for i in range(n + 1):
            snd, lag = (tic, 0.048 / 2 ** (2 / 12)) if i % 2 == 0 else (tac, 0.048 / 2 ** (-6 / 12))
            place(fx, snd, t0 + i * TICK_EVERY - lag, TICK_GAIN_DB + (0 if i % 2 == 0 else -1.5))

    # --- räkneverket 0 → 50: ett kort klick per siffra (samma kurva som bilden); inget extra klick på 50
    # (lås-klicket på 50 togs bort på beställarens begäran 2026-10-12)
    key = sfx("key-press")                    # ansats 0,075 s in
    t0 = a.T_S8 + a.FACT_NUM
    last_n, last_t = 0, -1.0
    for ms in range(0, 760):
        tt = t0 + ms / 1000
        n = int(round(50 * a.e_out3(min(1.0, ms / 750))))
        if n == 50:
            break
        if n != last_n and tt - last_t >= COUNT_MIN_GAP:
            place(fx, pan(key, 0.1 if n % 2 else -0.1), tt - 0.075, COUNT_GAIN_DB)
            last_n, last_t = n, tt

    # --- extraljusen slås på + siktet låser (+ samma tändljud svagare vid SE MER.)
    rv = REVEAL[reveal or CHOICE["reveal"]]
    layers(fx, rv, a.T_CLICK)
    layers(fx, SIGHT[sight or CHOICE["sight"]], a.T_DAR)
    layers(fx, rv, a.T_S10, SEE_MORE_DB)

    # --- slider: godkänd whoosh, oförändrad
    for (m0, _, _), p in zip(a.SLIDER_MOVES, (-0.5, 0.5, -0.4)):
        place(fx, pan(sfx("whoosh-short"), p), a.T_S7 + m0 + 0.18 - 0.165, WHOOSH_GAIN_DB)

    return fx * np.interp(ts, [0, a.DUR - 0.4, a.DUR], [1, 1, 0])[None]


def write_wav(path, mix):
    peak = np.abs(mix).max()
    assert peak < 0.99, f"klipper: {peak:.2f}"
    out = (mix.T * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    return peak


# ---------------------------------------------------------------- musik
# Stress fram till klicket (120 BPM = tic-tac-takten), lugnt och harmoniskt från klicket. Genererat med ACE-Step
# (library/tools/make_music.py), se music/README.txt. Musiken ligger i egen stem så att den kan bytas mot en låt.
MUSIC = {"stress": "music/stress-2.m4a", "track": "music/driving-ambition.mp3"}
# Vald låt efter klicket: Mixkit "Driving Ambition" (Stock Music Free License: reklam online/sociala medier ok,
# inte tv/radio, ingen remix). 100 BPM, 8-taktsfraser. Frasstarten 76,97 s landar på klicket, sluttonen 96,16 s
# (8 takter senare) på "SE MER.", efterklangen (en takt) tar slut när slutkortet kommer. Takter: build/beats-da.json.
TRACK_IN, TRACK_HIT, TRACK_RMS_DB = 76.97, 96.16, -22.0
STRESS_RMS_DB = -24.0        # stressdelens nivå (RMS) innan crescendot
CALM_RMS_DB = -25.0          # lugna delens nivå – under ljudeffekterna
BEAT = 0.5                   # 120 BPM
TICK_PHASE = V.TIMER1[0] % BEAT      # tic-tac slår på 0,30 + k·0,5 s


def onset_env(x, hop=512, n=2048):
    m = x.mean(0)
    frames = np.lib.stride_tricks.sliding_window_view(m, n)[::hop] * np.hanning(n)
    mag = np.abs(np.fft.rfft(frames, axis=1))
    flux = np.maximum(np.diff(np.log1p(mag), axis=0), 0).sum(1)
    return np.concatenate([[0], flux]), hop / SR


def beat_phase(x, period=BEAT):
    """Fas (s) för spårets slag med given period: den förskjutning där ansatserna summerar högst."""
    env, dt = onset_env(x)
    t = np.arange(len(env)) * dt
    best, best_p = -1.0, 0.0
    for p in np.arange(0, period, dt):
        k = np.round((t - p) / period)
        w = np.exp(-((t - (p + k * period)) / 0.02) ** 2)
        sc = (env * w).sum()
        if sc > best:
            best, best_p = sc, p
    return best_p


def active_span(x, floor_db=-40.0):
    m = x.mean(0)
    b = SR // 20
    rms = np.array([np.sqrt((m[i:i + b] ** 2).mean()) for i in range(0, len(m) - b, b)])
    on = rms > rms.max() * 10 ** (floor_db / 20)
    idx = np.where(on)[0]
    return idx[0] * b / SR, (idx[-1] + 1) * b / SR


def rms_db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def build_music():
    a = V
    music = np.zeros((2, N))
    ts = np.arange(N) / SR
    end1 = a.T_CLICK - 0.07                  # två bildrutor tystnad före klicket

    # --- stress: slagen på tic-tac, så sent i spåret som möjligt (mest uppbyggt) utan att ta med slutet
    st = load(os.path.join(HERE, MUSIC["stress"]))
    s0, s1 = active_span(st)
    ph = beat_phase(st[:, int(s0 * SR):int(s1 * SR)]) + s0
    start = (ph - TICK_PHASE) % BEAT
    while start + BEAT + end1 <= s1 - 0.3:
        start += BEAT
    seg = st[:, int(start * SR):int((start + end1) * SR)]
    st = st * db(STRESS_RMS_DB - rms_db(seg))
    place(music, st, 0.0, 0.0, start, start + end1, fade_in=0.12, fade_out=0.02)
    cres = np.interp(ts, [0, a.T_S5, end1], [0, 2.0, 5.0])          # crescendo mot klicket (dB)
    music *= np.where(ts < end1, db(cres), 1.0)[None]

    # --- låten: frasstart på klicket, sluttonen på SE MER., klingar ut till slutkortet (som är tyst)
    tr = load(os.path.join(HERE, MUSIC["track"]))
    drift = (a.T_S10 - a.T_CLICK) - (TRACK_HIT - TRACK_IN)
    assert abs(drift) < 0.03, f"klick→SE MER. ({a.T_S10 - a.T_CLICK:.3f}s) ska vara 8 takter ({TRACK_HIT - TRACK_IN:.3f}s)"
    loud = tr[:, int(TRACK_IN * SR):int((TRACK_IN + 9.5) * SR)]        # den drivande delen före utklingningen
    tr = tr * db(TRACK_RMS_DB - rms_db(loud))
    src_to = TRACK_IN + (a.T_S11 + 0.35 - a.T_CLICK)
    # +20 ms: låtens ansatser låg 17–36 ms före bildklippen; ljud får aldrig komma före bilden
    place(music, tr, a.T_CLICK + 0.02, 0.0, TRACK_IN, src_to, fade_in=0.01, fade_out=0.3)
    src0, c1 = TRACK_IN, src_to
    print(f"stress: start {start:.2f}s i spåret (fas {ph:.3f}); låten: {src0:.2f}–{c1:.2f}s, drift {drift * 1000:+.0f} ms")
    return music


def main():
    fx = build()
    music = build_music()
    write_wav(os.path.join(HERE, "build/sfx.wav"), fx)
    write_wav(os.path.join(HERE, "build/music.wav"), music)
    peak = write_wav(os.path.join(HERE, "build/mix.wav"), fx + music)
    print("build/mix.wav", CHOICE, MUSIC, f"topp {20 * np.log10(peak):.1f} dBFS")


if __name__ == "__main__":
    main()
