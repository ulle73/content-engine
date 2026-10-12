"""Ljudprovning: varje kandidat för helljuset (H1–H6) och siktet (S1–S6) i sitt moment, numrerad i bild.

  ../../.venv/Scripts/python.exe -I audition.py   -> out/ljudprovning.mp4
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A  # noqa: E402
import render as V  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, "build/audition")
FONT = r"C\:/Windows/Fonts/segoeuib.ttf"
os.makedirs(TMP, exist_ok=True)


def clip(idx, label, t0, t1, mix):
    wav = os.path.join(TMP, f"{idx:02d}.wav")
    A.write_wav(wav, mix[:, int(t0 * A.SR):int(t1 * A.SR)])
    out = os.path.join(TMP, f"{idx:02d}.mp4")
    vf = (f"scale=720:1280,drawbox=x=0:y=1150:w=720:h=130:color=black@0.7:t=fill,"
          f"drawtext=fontfile='{FONT}':text='{label}':fontcolor=white:fontsize=44:x=(w-tw)/2:y=1190")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}",
                    "-i", os.path.join(HERE, "out/video_noaudio.mp4"), "-i", wav, "-vf", vf,
                    "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-r", "30", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-ac", "2", "-shortest", out], check=True)
    return out


def main():
    parts, i = [], 0
    for k in A.REVEAL:
        mix = A.build(reveal=k, sight="S1")
        tag = " (vald)" if k == A.CHOICE["reveal"] else ""
        parts.append(clip(i, f"HELLJUS {k}{tag}", V.T_CLICK - 1.3, V.T_CLICK + 1.4, mix))
        i += 1
    for k in A.SIGHT:
        mix = A.build(sight=k)
        tag = " (vald)" if k == A.CHOICE["sight"] else ""
        parts.append(clip(i, f"SIKTE {k}{tag}", V.T_DAR - 0.6, V.T_DAR + 1.5, mix))
        i += 1
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    out = os.path.join(HERE, "out/ljudprovning.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)
    print(out)


if __name__ == "__main__":
    main()
