"""Ljudmix för "Vad händer med ditt friskvårdsbidrag vid årsskiftet?" (skills/ljud).

Bara riktiga ljud (Mixkit, se SOURCES.txt). Placering på uppmätt ansats, aldrig före bilden.
  python -I audio.py                 -> out/mix.wav + stems (musik/effekter), nivåer per moment
  python -I audio.py audition        -> out/ljudprovning.mp4 (kandidater numrerade i bild)
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 18.4  # bild 18,0 s scentid + 0,4 s sträckning (src/scene.js sceneTime)
FPS = 30

# Val (ändra efter ljudprovningen). Nyckel -> kandidat.
CHOICE = {"spanning": "A1", "var": "B1", "small": "I1", "kopp": "K1", "riv": "R1"}

MUSIC_A = {  # spänning 0–12,0 s; spår, startpunkt i spåret som hamnar på t=0,15
    "A1": ("music/m77.mp3", 2.299, "Running Out of Time (Mixkit 77)"),
    "A2": ("music/m92.mp3", 1.254, "Time Out (Mixkit 92)"),
    "A3": ("music/m32.mp3", 21.153, "Driving Ambition (Mixkit 32)"),
}
MUSIC_B = {  # vår 12,32 s -> slut; startpunkt i spåret som hamnar på t=12,32 (taktstart)
    "B1": ("music/m859.mp3", 24.232, "Under the Sun (Mixkit 859)"),
    "B2": ("music/m847.mp3", 2.587, "It's April (Mixkit 847)"),
    "B3": ("music/m91.mp3", 0.081, "Summer's Here (Mixkit 91)"),
}
IMPACT = {  # bollen slår igenom 31 dec (t=12,30): träff + papper
    "I1": [("sfx/golf14.mp3", 0.0)],  # Jonas 2026-10-13: golf-14 (Pixabay), nu bara som svag träff under rivljudet
    "I2": [("sfx/s2105.mp3", 0.0), ("sfx/s2384.mp3", -2.0)],
    "I3": [("sfx/s2122.mp3", 0.0), ("sfx/s2996.mp3", -4.0)],
}
RIP = {  # papper som rivs isär när bollen slår igenom 31 dec (Freesound, CC0; utklipp i sfx/rip/cut<id>.wav)
    "R1": ("sfx/rip/cut342541.wav", "Fast Paper Rip (Freesound 342541)"),
    "R2": ("sfx/rip/cut136496.wav", "Paper rip 1 (Freesound 136496)"),
    "R3": ("sfx/rip/cut272028.wav", "Ripping Paper (Freesound 272028)"),
    "R4": ("sfx/rip/cut211001.wav", "Paper Rip (Freesound 211001)"),
    "R5": ("sfx/rip/cut710163.wav", "Paper Rip 4 (Freesound 710163)"),
}
CUP = {  # bollen i koppen (t=14,78)
    "K1": [("sfx/putt-inbeeld.wav", 0.0)],  # Jonas 2026-10-13: Freesound 21878 inbeeld (CC0)
    "K2": [("sfx/s2070.mp3", 0.0)],
    "K3": [("sfx/s2077.mp3", 0.0)],
}
LABELS = {"spanning": MUSIC_A, "var": MUSIC_B, "small": IMPACT, "kopp": CUP, "riv": RIP}

# Verklig tid. Allt efter bläddringen ligger 0,4 s senare än i scentiden (sceneTime i src/scene.js).
SH = 0.4
T0_TEXT, T_STOP, T_WHOOSH_PEAK, T_IMPACT, T_SPRING, T_CUP = 0.15, 12.0 + SH, 12.27 + SH, 12.30 + SH, 12.32 + SH, 14.78 + SH
TEARS_SLOW = [0.75, 1.3]
TEARS_LAST = [t + SH for t in (10.35, 10.7, 11.0, 11.3, 11.6)]


def load(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, path), "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def onset(x, frac=0.05):
    """Ansats: första punkten där energin (5 ms glidande) passerar frac av max."""
    e = np.convolve((x ** 2).mean(1), np.ones(int(0.005 * SR)) / (0.005 * SR), "same")
    return int(np.argmax(e >= frac * e.max()))


def peak_idx(x):
    e = np.convolve((x ** 2).mean(1), np.ones(int(0.005 * SR)) / (0.005 * SR), "same")
    return int(np.argmax(e))


def peak_rms(x, t, span=0.2, w=0.05):
    """Högsta RMS (dB) i 50 ms-fönster under span sekunder från t."""
    a = int(t * SR); seg = x[a: a + int(span * SR)]
    k = int(w * SR)
    if len(seg) < k:
        return -120.0
    e = np.convolve((seg ** 2).mean(1), np.ones(k) / k, "valid")
    return float(10 * np.log10(e.max() + 1e-12))


def db(g):
    return 10 ** (g / 20)


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    n = len(x)
    if fin:
        k = min(n, int(fin * SR)); x[:k] *= np.linspace(0, 1, k)[:, None]
    if fout:
        k = min(n, int(fout * SR)); x[n - k:] *= np.linspace(1, 0, k)[:, None]
    return x


class Track:
    def __init__(self):
        self.buf = np.zeros((int(DUR * SR) + SR, 2), np.float32)
        self.events = []

    def place(self, x, t, gain_db=0.0, align="onset", name="", over=None):
        """Lägg x så att dess ansats (eller topp) hamnar på t. over=(musik, dB): nivå relativt musiken i momentet."""
        off = {"onset": onset(x), "peak": peak_idx(x), "start": 0}[align]
        if over is not None:
            ref, rel = over
            gain_db = rel + max(peak_rms(ref, t), -40.0) - peak_rms(x, off / SR)
        i = int(round(t * SR)) - off
        if i < 0:
            x, i = x[-i:], 0
        n = min(len(x), len(self.buf) - i)
        self.buf[i:i + n] += x[:n] * db(gain_db)
        self.events.append((name, t))


def music_segment(path, start_in_track, t_at, t_from, t_to, fin=0.02, fout=0.03):
    x = load(path)
    a = int((start_in_track + (t_from - t_at)) * SR)
    seg = x[max(0, a): max(0, a) + int((t_to - t_from) * SR)]
    return fade(seg, fin, fout)


def build(choice):
    mus, fx = Track(), Track()
    # --- musik A: spänning, hårt stopp vid 12,0 (tystnad före bollen) ---
    p, s, _ = MUSIC_A[choice["spanning"]]
    mus.place(music_segment(p, s, T0_TEXT, 0.0, T_STOP, fin=0.08, fout=0.04), 0.0, -2.0, "start", "musik A")
    # --- musik B: våren från smällen, tonar ut i irisen ---
    p, s, _ = MUSIC_B[choice["var"]]
    seg = music_segment(p, s, T_SPRING, T_SPRING, DUR, fin=0.01, fout=0.55)
    mus.place(seg, T_SPRING, -3.0, "start", "musik B")

    # --- papper ---
    turn, tear, tick, flutter = load("sfx/s1104.mp3"), load("sfx/s2384.mp3"), load("sfx/s1061.mp3"), load("sfx/s1102.mp3")
    tick = fade(tick[: onset(tick) + int(0.3 * SR)], 0, 0.08)  # kort svans: tyst före bollen
    for t in TEARS_SLOW:
        fx.place(turn, t, 0, "onset", "blad", over=(mus.buf, 3.0))
    fl = fade(flutter[: int(8.65 * SR)], 0.4, 0.8)
    fx.place(fl, 1.75, -4.0, "start", "bläddring")
    for i, t in enumerate(TEARS_LAST):
        fx.place(tear, t, 0, "onset", "riv", over=(mus.buf, 1.0 + i * 0.4))
        fx.place(tick, t + 0.02, 0, "onset", "tick", over=(mus.buf, -2.0 + i * 0.4))
    # --- eld ---
    match, crackle = load("sfx/s2590.mp3"), load("sfx/s1330.mp3")
    fx.place(fade(match[: int(1.6 * SR)], 0, 0.5), 0.9, 0, "onset", "tändsticka", over=(mus.buf, 0.0))
    cr = fade(crackle[int(2 * SR): int(2 * SR) + int((T_STOP - 1.1) * SR)], 1.0, 0.04)  # tyst före bollen
    cr *= db(np.linspace(-12.0, -3.0, len(cr)))[:, None]  # växer med elden
    fx.place(cr, 1.1, 0.0, "start", "sprak")
    # --- bollen ---
    wh = load("sfx/whoosh-short.mp3")  # Pixabay; topp ~0,17 s in -> ~12,27 s, börjar när bollen syns
    fx.place(wh, 12.1 + SH, -14.0 - peak_rms(wh, 0), "start", "sus")
    # Smällen = papper som rivs isär (bär momentet) + golfträffen svagt under.
    # Jonas 2026-10-13: "halvera ljudet" -> hela momentet ~6 dB lägre än förra versionen (-4,5 -> ~-10,5 dB RMS).
    rip = load(RIP[choice["riv"]][0])
    fx.place(rip, T_IMPACT, -11.0 - peak_rms(rip, onset(rip) / SR), "onset", "riv-smäll")
    for path, g in IMPACT[choice["small"]]:
        x = load(path)
        fx.place(x, T_IMPACT, -18.0 + g - peak_rms(x, onset(x) / SR), "onset", "träff")
    tap = load("sfx/s2073.mp3")
    fx.place(tap, 13.6 + SH, 0, "onset", "studs 1", over=(mus.buf, 3.0))
    fx.place(tap, 14.02 + SH, 0, "onset", "studs 2", over=(mus.buf, 1.0))
    for path, g in CUP[choice["kopp"]]:
        fx.place(load(path), T_CUP, 0, "onset", "kopp", over=(mus.buf, 6.0 + g))
    fx.place(load("sfx/s1530.mp3"), 14.98 + SH, 0, "onset", "kupong", over=(mus.buf, 0.0))

    n = int(DUR * SR)
    return mus.buf[:n], fx.buf[:n], fx.events


def rms_db(x, t, w=0.05):
    a = int((t - w / 2) * SR); seg = x[max(0, a): a + int(w * SR)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)


def write_wav(path, x):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", path],
                   input=x.astype(np.float32).tobytes(), check=True)


def measure(src):
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", "loudnorm=I=-14:TP=-1.0:LRA=20:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    return json.loads(m[m.rfind("{"):m.rfind("}") + 1])


def loudnorm(src, dst, limit=0.66):
    """Hela mixen höjs lika mycket till -14 LUFS (balansen bevaras), sedan en limiter som håller toppen under -1 dBTP."""
    j = measure(src)
    gain = -14.0 - float(j["input_i"])
    for _ in range(3):  # limitern sänker nivån lite; justera tills -14 ±0,3
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        f"volume={gain:.2f}dB,lowpass=f=15500:poles=2,aresample=192000,alimiter=limit={limit}:attack=0.5:release=50:level=disabled,aresample={SR}",
                        dst], check=True)
        k = measure(dst)
        if abs(float(k["input_i"]) + 14.0) <= 0.3:
            break
        gain += -14.0 - float(k["input_i"])
    return {**j, "out_i": k["input_i"], "out_tp": k["input_tp"]}


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    mus, fx, events = build(CHOICE)
    mix = mus + fx
    write_wav(os.path.join(HERE, "out", "stem-musik.wav"), mus)
    write_wav(os.path.join(HERE, "out", "stem-effekter.wav"), fx)
    write_wav(os.path.join(HERE, "out", "mix-raw.wav"), mix)
    j = loudnorm(os.path.join(HERE, "out", "mix-raw.wav"), os.path.join(HERE, "out", "mix.wav"))
    print(f"loudness: in {j['input_i']} LUFS / {j['input_tp']} dBTP -> ut {j['out_i']} LUFS / {j['out_tp']} dBTP")
    print("nivå per moment (RMS 50 ms, före normalisering): effekter / musik")
    for name, t in events:
        if name in ("bläddring", "sprak", "musik A", "musik B"):
            continue
        print(f"  {t:6.2f} s {name:12s} fx {peak_rms(fx, t):6.1f} dB   musik {peak_rms(mus, t):6.1f} dB")


def audition():
    """Varje kandidat i sitt sammanhang, numrerad i bild."""
    video = os.path.join(HERE, "out", "bild-9x16.mp4")
    parts = []
    tests = [("riv", 11.9, 13.9), ("spanning", 3.0, 9.0), ("var", 12.4, 18.4)]  # kopp vald av Jonas 2026-10-13
    for key, a, b in tests:
        for cand, val in LABELS[key].items():
            ch = dict(CHOICE, **{key: cand})
            mus, fx, _ = build(ch)
            seg = (mus + fx)[int(a * SR): int(b * SR)]
            wav = os.path.join(HERE, "out", f"aud-{cand}.wav")
            write_wav(wav, seg * db(4))
            name = val[-1] if isinstance(val, tuple) else " + ".join(os.path.basename(p) for p, _ in val)
            out = os.path.join(HERE, "out", f"aud-{cand}.mp4")
            label = f"{cand}  {name}".replace(":", "\\:").replace("'", "")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", video, "-i", wav,
                            "-vf", f"drawbox=y=1500:h=200:w=iw:color=black@0.7:t=fill,drawtext=fontfile=../../engine/ad_studio/fonts/Inter-Bold.ttf:text='{label}':x=(w-tw)/2:y=1570:fontsize=46:fontcolor=white",
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True, cwd=HERE)
            parts.append(out)
    lst = os.path.join(HERE, "out", "aud-list.txt")
    with open(lst, "w") as f:
        f.write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(HERE, "out", "ljudprovning.mp4")], check=True)
    print("out/ljudprovning.mp4")


if __name__ == "__main__":
    audition() if sys.argv[1:] == ["audition"] else main()
