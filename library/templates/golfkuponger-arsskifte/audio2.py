"""Ljudmix för spola tillbaka-versionen (src/scene2.js). Verklig tid. Återanvänder verktygen i audio.py.
  python -I audio2.py              -> out/mix2.wav + stems
  python -I audio2.py audition     -> out/ljudprovning2.mp4 (larm L1–L5, smäll M1–M3, knapp P1–P3)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import audio as A  # noqa: E402

A.DUR = DUR = 29.75
SR = A.SR
CHOICE = {"spanning": "A1", "var": "B1", "riv": "R1", "larm": "L3", "smack": "M2", "knapp": "P1", "grat": "G1"}  # L3, M2, P1 valda av Jonas 2026-10-13 – ändra inte
LARM = {k: (f"sfx/v2/cut/{k}.wav", n) for k, n in [("L1", "Air Raid Siren (Freesound 157463, CC0)"), ("L2", "Air raid siren Prague (Freesound 382611, CC0)"),
                                                   ("L3", "Facility alarm (Mixkit 999)"), ("L4", "Security facility breach alarm (Mixkit 994)"), ("L5", "Emergency alert alarm (Mixkit 1007)")]}
SMACK = {k: (f"sfx/v2/cut/{k}.wav", n) for k, n in [("M1", "Big cinematic impact (Mixkit 788)"), ("M2", "Hard horror hit drum (Mixkit 565)"), ("M3", "Short bass hit (Mixkit 2299)")]}
KNAPP = {k: (f"sfx/v2/cut/{k}.wav", n) for k, n in [("P1", "Cassette Tape Button (Freesound 423870, CC0)"), ("P2", "Casio cassette Play Button (Freesound 624637, CC0)"), ("P3", "Cassette player button (Freesound 572138, CC0)")]}
# Gråt: Jonas fil (Pixabay, "crying man effect" av peterpiotr), 2 s-utdrag: (start i filen, beskrivning)
GRAT = {"G1": (0.45, "gråten bryter ut (0,45 s in)"), "G2": (12.2, "kraftigaste gråten (12,2 s in)"), "G3": (18.4, "snyftande gråt (18,4 s in)")}
LABELS = {"larm": LARM, "smack": SMACK, "knapp": KNAPP, "grat": {k: (None, v[1]) for k, v in GRAT.items()}}

# Händelser (verklig tid, se M i src/scene2.js)
STOP_MUSIC, BALL1, IMPACT1, SPRING1, SIGN = 9.05, 9.15, 9.35, 9.37, 12.55
CRY, PAUSE, REW, PLAY, SLOW = 14.4, 16.4, 20.0, 22.0, (22.9, 23.4)
BALL2, IMPACT2, SPRING2, BOUNCE2, CUP2, COUPON2 = 23.85, 24.05, 24.07, (25.35, 25.77), 26.53, 26.73
TEARS_SLOW, TEARS_LAST = (0.75, 1.25), (6.95, 7.3, 7.6, 7.9, 8.2)


def build(ch):
    mus, fx = A.Track(), A.Track()
    A.DUR = DUR
    mus.buf = np.zeros((int(DUR * SR) + SR, 2), np.float32); fx.buf = np.zeros_like(mus.buf)
    # musik: spänning till 12-slaget, vår i 1,2 s som tvärklipps av förbudsmärket, vår igen i varv 2
    p, s, _ = A.MUSIC_A[ch["spanning"]]
    mus.place(A.music_segment(p, s, 0.15, 0.0, STOP_MUSIC, fin=0.08, fout=0.04), 0.0, -2.0, "start", "musik A")
    p, s, _ = A.MUSIC_B[ch["var"]]
    mus.place(A.music_segment(p, s, SPRING1, SPRING1, SIGN, fin=0.01, fout=0.02), SPRING1, -3.0, "start", "musik B1")
    mus.place(A.music_segment(p, s, SPRING2, SPRING2, DUR, fin=0.01, fout=0.55), SPRING2, -3.0, "start", "musik B2")

    turn, tear, tick, flutter = A.load("sfx/s1104.mp3"), A.load("sfx/s2384.mp3"), A.load("sfx/s1061.mp3"), A.load("sfx/s1102.mp3")
    tick = A.fade(tick[: A.onset(tick) + int(0.3 * SR)], 0, 0.08)
    for t in TEARS_SLOW:
        fx.place(turn, t, 0, "onset", "blad", over=(mus.buf, 3.0))
    fx.place(A.fade(flutter[: int(5.2 * SR)], 0.4, 0.8), 1.6, -4.0, "start", "bläddring")
    for i, t in enumerate(TEARS_LAST):
        fx.place(tear, t, 0, "onset", "riv", over=(mus.buf, 1.0 + i * 0.4))
        fx.place(tick, t + 0.02, 0, "onset", "tick", over=(mus.buf, -2.0 + i * 0.4))
    match, crackle = A.load("sfx/s2590.mp3"), A.load("sfx/s1330.mp3")
    fx.place(A.fade(match[: int(1.6 * SR)], 0, 0.5), 0.6, 0, "onset", "tändsticka", over=(mus.buf, 0.0))
    cr = A.fade(crackle[int(2 * SR): int(2 * SR) + int((STOP_MUSIC - 0.8) * SR)], 1.0, 0.04)
    cr *= A.db(np.linspace(-12.0, -2.0, len(cr)))[:, None]
    fx.place(cr, 0.8, 0.0, "start", "sprak")
    cr2 = A.fade(crackle[int(9 * SR): int(9 * SR) + int((IMPACT2 - PLAY) * SR)], 0.05, 0.05) * A.db(-6.0)
    fx.place(cr2, PLAY, 0.0, "start", "sprak 2")

    wh, rip, hit = A.load("sfx/whoosh-short.mp3"), A.load(A.RIP[ch["riv"]][0]), A.load("sfx/golf14.mp3")
    for b, i in ((BALL1, IMPACT1), (BALL2, IMPACT2)):
        fx.place(wh, b, -14.0 - A.peak_rms(wh, 0), "start", "sus")
        fx.place(rip, i, -11.0 - A.peak_rms(rip, A.onset(rip) / SR), "onset", "riv-smäll")
        fx.place(hit, i, -18.0 - A.peak_rms(hit, A.onset(hit) / SR), "onset", "träff")

    # förbudsmärket: smäll (starkast i filmen) + larm som håller i sig under gråten och klipps av pausen
    sm = A.load(SMACK[ch["smack"]][0])
    fx.place(sm, SIGN, -3.0 - A.peak_rms(sm, A.onset(sm) / SR), "onset", "märke")
    larm = A.load(LARM[ch["larm"]][0])
    need = int((PAUSE - SIGN) * SR)
    loop = np.concatenate([larm] * (need // len(larm) + 2))[:need]
    full, dip = int((CRY - SIGN) * SR), int(0.6 * SR)
    curve = np.concatenate([np.zeros(full), np.linspace(0, -18, dip), np.full(max(0, need - full - dip), -18.0)])[:need]
    loop = A.fade(loop, 0.02, 0.03) * A.db(curve)[:, None]
    fx.place(loop, SIGN + 0.02, -12.0 - A.peak_rms(larm, 0.2), "start", "larm")

    cry = A.load("sfx/v2/cry-peterpiotr.mp3")
    a0 = int(GRAT[ch["grat"]][0] * SR)
    cry = A.fade(cry[a0:a0 + int((PAUSE - CRY) * SR)], 0.04, 0.03)  # klipps av pausklicket
    fx.place(cry, CRY, -8.0 - A.peak_rms(cry, 0, span=1.5), "start", "gråt")
    for t in SLOW:
        fx.place(tear, t, -14.0 - A.peak_rms(tear, A.onset(tear) / SR), "onset", "lugnt blad")
        fx.place(tick, t + 0.02, -17.0 - A.peak_rms(tick, A.onset(tick) / SR), "onset", "tick 2")
    kn = A.load(KNAPP[ch["knapp"]][0])
    for t, name in ((PAUSE, "paus"), (PLAY, "play")):
        fx.place(kn, t, -8.0 - A.peak_rms(kn, A.onset(kn) / SR), "onset", name)
    rw = A.load("sfx/rewind-1088.mp3")
    rw = A.fade(rw[: int((PLAY - REW + 0.05) * SR)], 0.03, 0.15)
    fx.place(rw, REW, -9.0 - A.peak_rms(rw, 1.0, span=1.0), "start", "spola")

    tap = A.load("sfx/s2073.mp3")
    fx.place(tap, BOUNCE2[0], 0, "onset", "studs 1", over=(mus.buf, 3.0))
    fx.place(tap, BOUNCE2[1], 0, "onset", "studs 2", over=(mus.buf, 1.0))
    for path, g in A.CUP["K1"]:
        fx.place(A.load(path), CUP2, 0, "onset", "kopp", over=(mus.buf, 6.0 + g))
    fx.place(A.load("sfx/s1530.mp3"), COUPON2, 0, "onset", "kupong", over=(mus.buf, 0.0))
    n = int(DUR * SR)
    return mus.buf[:n], fx.buf[:n], fx.events


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    mus, fx, events = build(CHOICE)
    A.write_wav(os.path.join(HERE, "out", "stem2-musik.wav"), mus)
    A.write_wav(os.path.join(HERE, "out", "stem2-effekter.wav"), fx)
    A.write_wav(os.path.join(HERE, "out", "mix2-raw.wav"), mus + fx)
    j = A.loudnorm(os.path.join(HERE, "out", "mix2-raw.wav"), os.path.join(HERE, "out", "mix2.wav"), limit=0.6)  # tät decembermix: marginal för AAC
    print(f"loudness: in {j['input_i']} LUFS -> ut {j['out_i']} LUFS / {j['out_tp']} dBTP")
    for name, t in events:
        if name in ("märke", "riv-smäll", "larm", "gråt", "paus", "play", "spola", "lugnt blad", "kopp"):
            print(f"  {t:6.2f} s {name:10s} fx {A.peak_rms(fx, t):6.1f} dB   musik {A.peak_rms(mus, t):6.1f} dB")


def audition():
    video = os.path.join(HERE, "out", "bild2-9x16.mp4")  # gråt-provning (larm, smäll och knapp är valda)
    parts = []
    for key, a, b in [("grat", 13.9, 16.9)]:
        for cand, (_, name) in LABELS[key].items():
            mus, fx, _ = build(dict(CHOICE, **{key: cand}))
            wav = os.path.join(HERE, "out", f"aud2-{cand}.wav")
            A.write_wav(wav, (mus + fx)[int(a * SR): int(b * SR)] * A.db(4))
            out = os.path.join(HERE, "out", f"aud2-{cand}.mp4")
            label = f"{cand}  {name}".replace(":", "\\:").replace("'", "").replace(",", "\\,")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", video, "-i", wav,
                            "-vf", f"drawbox=y=1500:h=200:w=iw:color=black@0.7:t=fill,drawtext=fontfile=../../engine/ad_studio/fonts/Inter-Bold.ttf:text='{label}':x=(w-tw)/2:y=1570:fontsize=40:fontcolor=white",
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True, cwd=HERE)
            parts.append(out)
    lst = os.path.join(HERE, "out", "aud2-list.txt")
    with open(lst, "w") as f:
        f.write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(HERE, "out", "ljudprovning2.mp4")], check=True)
    print("out/ljudprovning2.mp4")


if __name__ == "__main__":
    audition() if sys.argv[1:] == ["audition"] else main()
