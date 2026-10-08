"""Review harness for rendered videos (ffmpeg + Pillow): look at the film before calling it done.

    python review.py frames  film.mp4 --every 0.5 --out work/prompts/x/frames       # one PNG every N s
    python review.py sheet   film.mp4 --every 1 --cols 5 --out sheet.jpg             # contact sheet with timestamps
    python review.py strip   film.mp4 --at 4.2 --span 0.4 --out strip.jpg            # EVERY frame around a moment
    python review.py phone   film.mp4 --at 1.0,6.0 --width 390 --out phone.jpg        # phone-size readability test
    python review.py loop    film.mp4                                                # first vs last frame (+ motion)
    python review.py same    a.mp4 b.mp4                                             # determinism: identical frames?

Open the produced images with an image viewer / the Read tool and actually look at them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


def probe(path: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", path],
                         check=True, capture_output=True, text=True).stdout
    data = json.loads(out)
    s = data["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"w": s["width"], "h": s["height"], "fps": float(num) / float(den), "duration": float(data["format"]["duration"])}


def frame_at(path: str, t: float) -> Image.Image:
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "png", "-"], check=True, capture_output=True).stdout
    return Image.open(BytesIO(png)).convert("RGB")


def all_frames(path: str, start: float = 0, span: float | None = None) -> list[Image.Image]:
    info = probe(path)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.4f}", "-i", path]
    if span:
        cmd += ["-t", f"{span:.4f}"]
    raw = subprocess.run(cmd + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    size = info["w"] * info["h"] * 3
    return [Image.frombytes("RGB", (info["w"], info["h"]), raw[i:i + size]) for i in range(0, len(raw) - size + 1, size)]


def grid(images: list[Image.Image], labels: list[str], cols: int, width: int) -> Image.Image:
    w = width
    h = int(images[0].height * w / images[0].width)
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 22)), "#111")
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(zip(images, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 22)
        sheet.paste(im.resize((w, h)), (x, y + 22))
        draw.text((x + 6, y + 4), label, fill="#eee")
    return sheet


def times_every(duration: float, every: float) -> list[float]:
    n = int(duration / every) + 1
    return [min(i * every, duration - 0.05) for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["frames", "sheet", "strip", "phone", "loop", "same"])
    ap.add_argument("video")
    ap.add_argument("other", nargs="?")
    ap.add_argument("--every", type=float, default=1.0)
    ap.add_argument("--at", default="0")
    ap.add_argument("--span", type=float, default=0.4)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--out", default="review.jpg")
    a = ap.parse_args()
    info = probe(a.video)

    if a.cmd == "frames":
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for t in times_every(info["duration"], a.every):
            frame_at(a.video, t).save(out / f"t{t:07.2f}.png")
        print("frames ->", out)
    elif a.cmd == "sheet":
        ts = times_every(info["duration"], a.every)
        grid([frame_at(a.video, t) for t in ts], [f"{t:.2f}s" for t in ts], a.cols, a.width).save(a.out, quality=88)
        print("sheet ->", a.out)
    elif a.cmd == "strip":
        at = float(a.at.split(",")[0])
        start = max(0.0, at - a.span / 2)
        frames = all_frames(a.video, start, a.span)
        labels = [f"{start + i / info['fps']:.3f}s" for i in range(len(frames))]
        grid(frames, labels, min(a.cols * 2, len(frames)), a.width).save(a.out, quality=88)
        print("strip ->", a.out, f"({len(frames)} frames)")
    elif a.cmd == "phone":
        ts = [float(x) for x in a.at.split(",")]
        grid([frame_at(a.video, t) for t in ts], [f"{t:.2f}s @ {a.width}px" for t in ts], len(ts), a.width).save(a.out, quality=92)
        print("phone ->", a.out, "(view at 100%: can every word be read?)")
    elif a.cmd == "loop":
        frames = all_frames(a.video)
        first, last, second, before_last = frames[0], frames[-1], frames[1], frames[-2]
        def diff(x, y):
            return sum(abs(p - q) for p, q in zip(x.tobytes(), y.tobytes())) / len(x.tobytes())
        pos = diff(first, last)
        vel = abs(diff(first, second) - diff(before_last, last))
        print(json.dumps({"first_vs_last_mean_abs": round(pos, 3), "velocity_mismatch": round(vel, 3),
                          "seamless": pos < 2 and vel < 2}))
    elif a.cmd == "same":
        if not a.other:
            raise SystemExit("same needs two videos")
        ha = [hashlib.sha1(f.tobytes()).hexdigest() for f in all_frames(a.video)]
        hb = [hashlib.sha1(f.tobytes()).hexdigest() for f in all_frames(a.other)]
        bad = [i for i, (x, y) in enumerate(zip(ha, hb)) if x != y]
        print(json.dumps({"frames": [len(ha), len(hb)], "different_frames": bad[:50], "identical": not bad and len(ha) == len(hb)}))


if __name__ == "__main__":
    main()
