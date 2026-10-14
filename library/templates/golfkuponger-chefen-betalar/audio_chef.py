"""Ljudmix för "Låt chefen betala din golf" (src/chef-film.js). Verklig tid. Verktyg från audio.py.
  python -I audio_chef.py             -> out/mix.wav + stems
  python -I audio_chef.py audition    -> out/ljudprovning.mp4 (musik M1–M3, bock C1–C3, stämpel ST1–ST2)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import audio as A  # noqa: E402

DUR = 23.75
SR = A.SR
CHOICE = {"musik": "M1", "bock": "C1", "stampel": "ST1"}
MUSIK = {"M1": ("music/m2.mp3", 0.244, "Comical (Mixkit 2, 140 BPM)"), "M2": ("music/m10.mp3", 0.244, "Playful (Mixkit 10, 130 BPM)"),
         "M3": ("music/m9.mp3", 0.441, "Kidding Around (Mixkit 9, 88 BPM)")}
BOCK = {"C1": ("sfx/s2867.mp3", "Confirmation tone (Mixkit 2867)"), "C2": ("sfx/s2870.mp3", "Correct answer tone (Mixkit 2870)"),
        "C3": ("sfx/s951.mp3", "Positive notification (Mixkit 951)")}
STAMPEL = {"ST1": ("sfx/bank-smack.wav", "Dov trumma (ljudbanken, Mixkit 565)"), "ST2": ("sfx/s197.mp3", "Knackning tung trädörr (Mixkit 197)")}
LABELS = {"musik": {k: v[2] for k, v in MUSIK.items()}, "bock": {k: v[1] for k, v in BOCK.items()}, "stampel": {k: v[1] for k, v in STAMPEL.items()}}

DOOR, CRICKETS = 0.5, (1.15, 3.45)
MUSIC_A, MUSIC_A_STOP, STAMP, MUSIC_B = 3.6, 14.6, 15.8, 15.85
TAPS = (4.6, 6.2, 7.45, 9.42, 11.0)
SCROLL, SLIDE, TYPE0, CHECK, MAIL = 4.75, 6.45, 7.6, 9.95, 10.6
PAPER, TICKS, WIPE = 13.5, (14.65, 14.95, 15.25, 15.55), 18.3


def build(ch):
    mus, fx = A.Track(), A.Track()
    mus.buf = np.zeros((int(DUR * SR) + SR, 2), np.float32); fx.buf = np.zeros_like(mus.buf)
    p, s, _ = MUSIK[ch["musik"]]
    mus.place(A.music_segment(p, s, MUSIC_A, MUSIC_A, MUSIC_A_STOP, fin=0.15, fout=0.05), MUSIC_A, -4.0, "start", "musik A")
    mus.place(A.music_segment("music/m859.mp3", 24.232, MUSIC_B, MUSIC_B, DUR, fin=0.01, fout=0.55), MUSIC_B, -3.0, "start", "musik B")

    def put(path, t, rel, name, align="onset", ref=None, absolute=None, cut=None):
        x = A.load(path)
        if cut:
            x = A.fade(x[: int(cut * SR)], 0, min(0.1, cut / 3))
        if absolute is not None:
            fx.place(x, t, absolute - A.peak_rms(x, A.onset(x) / SR), align, name)
        else:
            fx.place(x, t, 0, align, name, over=(mus.buf, rel))

    # dörren och den pinsamma tystnaden (ingen musik än)
    put("sfx/s195.mp3", DOOR, 0, "dörr", absolute=-12.0)
    cr = A.load("sfx/s1788.mp3")
    cr = A.fade(cr[int(1.0 * SR): int(1.0 * SR) + int((CRICKETS[1] - CRICKETS[0]) * SR)], 0.25, 0.4)
    fx.place(cr, CRICKETS[0], -16.0 - A.peak_rms(cr, 0.5, span=1.0), "start", "syrsor")
    # mobilen
    put("sfx/whoosh-short.mp3", MUSIC_A - 0.05, 0, "mobil upp", align="start", absolute=-16.0)
    for t in TAPS:
        put("sfx/click-soft.mp3", t, 2.0, "tryck")
    put("sfx/whoosh-short.mp3", SCROLL, -3.0, "scroll", align="start")
    put("sfx/s1530.mp3", SLIDE, 0.0, "sidbyte")
    ty = A.load("sfx/typing.mp3")
    ty = A.fade(ty[A.onset(ty): A.onset(ty) + int(1.0 * SR)], 0.01, 0.08)
    fx.place(ty, TYPE0, 0, "start", "skriver", over=(mus.buf, 0.0))
    put(BOCK[ch["bock"]][0], CHECK, 3.0, "bock")
    put("sfx/s2354.mp3", MAIL, 1.0, "mejl")
    # chefen
    put("sfx/s1530.mp3", PAPER, 0.0, "kvitto glider")
    tick = A.load("sfx/s1061.mp3")
    tick = A.fade(tick[: A.onset(tick) + int(0.3 * SR)], 0, 0.08)
    for i, t in enumerate(TICKS):
        fx.place(tick, t, -14.0 + i * 1.0 - A.peak_rms(tick, A.onset(tick) / SR), "onset", "tick")
    put(STAMPEL[ch["stampel"]][0], STAMP, 0, "stämpel", absolute=-4.0)   # hjältljudet
    put("sfx/whoosh-short.mp3", WIPE, -2.0, "till banan", align="start")
    n = int(DUR * SR)
    return mus.buf[:n], fx.buf[:n], fx.events


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    mus, fx, events = build(CHOICE)
    A.write_wav(os.path.join(HERE, "out", "stem-musik.wav"), mus)
    A.write_wav(os.path.join(HERE, "out", "stem-effekter.wav"), fx)
    A.write_wav(os.path.join(HERE, "out", "mix-raw.wav"), mus + fx)
    j = A.loudnorm(os.path.join(HERE, "out", "mix-raw.wav"), os.path.join(HERE, "out", "mix.wav"), limit=0.6)
    print(f"loudness: in {j['input_i']} LUFS -> ut {j['out_i']} LUFS / {j['out_tp']} dBTP")
    for name, t in events:
        if name in ("dörr", "tryck", "bock", "mejl", "stämpel", "skriver"):
            print(f"  {t:6.2f} s {name:10s} fx {A.peak_rms(fx, t):6.1f} dB   musik {A.peak_rms(mus, t):6.1f} dB")


def audition():
    video = os.path.join(HERE, "out", "bild-9x16.mp4")
    parts = []
    for key, a, b in [("musik", 3.6, 9.6), ("bock", 9.3, 11.3), ("stampel", 14.4, 16.9)]:
        for cand, name in LABELS[key].items():
            mus, fx, _ = build(dict(CHOICE, **{key: cand}))
            wav = os.path.join(HERE, "out", f"aud-{cand}.wav")
            A.write_wav(wav, (mus + fx)[int(a * SR): int(b * SR)] * A.db(4))
            out = os.path.join(HERE, "out", f"aud-{cand}.mp4")
            label = f"{cand}  {name}".replace(":", "\\:").replace("'", "").replace(",", "\\,")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", video, "-i", wav,
                            "-vf", f"drawbox=y=1500:h=200:w=iw:color=black@0.7:t=fill,drawtext=fontfile=../../engine/ad_studio/fonts/Inter-Bold.ttf:text='{label}':x=(w-tw)/2:y=1570:fontsize=40:fontcolor=white",
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True, cwd=HERE)
            parts.append(out)
    lst = os.path.join(HERE, "out", "aud-list.txt")
    with open(lst, "w") as f:
        f.write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(HERE, "out", "ljudprovning.mp4")], check=True)
    print("out/ljudprovning.mp4")


if __name__ == "__main__":
    audition() if sys.argv[1:] == ["audition"] else main()
