#!/usr/bin/env python3
"""
Render a CSS-animated library block to a real mp4 — the thing that was missing.

Every block in ui-blocks/ loops on CSS animations and accepts ?seek=<s>.
This shoots one headless frame per timestep, in parallel, and assembles them. That is
what turns the library from screenshots into animation.

    python scripts/block-render.py "skills-beat.html?mode=slash" out.mp4 --start 0 --dur 6 --fps 20

Frames are shot concurrently (each Chrome launch is ~2.9s, so 6 at a time ≈ 1 min for 120).
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, os, shlex, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

CHROME = os.environ.get("CHROME") or next((p for p in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome") if os.path.exists(p)),
    "chrome")
# serve the skill folder first:  cd library/kits/nextphase/skills/nextphase-short-editing
#                                python -m http.server 8777 --bind 127.0.0.1
BASE   = os.environ.get("BLOCK_BASE", "http://127.0.0.1:8777/ui-blocks/")

def shoot(args):
    """Shoot one frame. Chrome fails intermittently (~1 in 100); a missing frame used to
    truncate the whole mp4 at the gap, silently — the render looked fine and was short.
    Retry, and let the caller fill anything still missing."""
    url, out, w, h, bg = args
    for attempt in range(3):
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               f"--window-size={w},{h}", "--virtual-time-budget=1500"]
        if bg:
            # paints the page ground; pair with ?plate=none so the block draws straight
            # onto it (the coral HALF itself, not a coral frame around a cream picture)
            cmd.append(f"--default-background-color={bg}")
        cmd += [f"--screenshot={out}", url]
        subprocess.run(cmd,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return True
    return False

def main():
    p = argparse.ArgumentParser()
    p.add_argument("block")                       # e.g. "skills-beat.html?mode=slash"
    p.add_argument("out")
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--dur",   type=float, default=6.0)
    p.add_argument("--fps",   type=int,   default=20)
    p.add_argument("--width", type=int,   default=1080)
    p.add_argument("--height",type=int,   default=1920)
    p.add_argument("--jobs",  type=int,   default=6)
    p.add_argument("--bg", default="", help="page ground as RRGGBBAA, e.g. D97757FF for the coral half")
    a = p.parse_args()

    n = int(round(a.dur * a.fps))
    sep = "&" if "?" in a.block else "?"
    tmp = tempfile.mkdtemp(prefix="blockrender-")
    tasks = []
    for i in range(n):
        t = a.start + i / a.fps
        url = f"{BASE}{a.block}{sep}seek={t:.3f}"
        tasks.append((url, os.path.join(tmp, f"f{i:05d}.png"), a.width, a.height, a.bg))

    print(f"shooting {n} frames @ {a.fps}fps ({a.dur}s) — {a.jobs} at a time")
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        done = list(ex.map(shoot, tasks))
    missing = done.count(False)
    if missing:
        # Fill each hole from its nearest good neighbour. Without this ffmpeg's image2
        # demuxer stops dead at the first gap and writes a SHORT video with no error.
        import shutil
        good = [i for i, ok in enumerate(done) if ok]
        if not good:
            sys.exit("every frame failed — is the block server on 8777 up?")
        for i, ok in enumerate(done):
            if ok:
                continue
            src = min(good, key=lambda g: abs(g - i))
            shutil.copyfile(tasks[src][1], tasks[i][1])
        print(f"  WARNING {missing} frame(s) failed; filled from nearest neighbour "
              f"(indices {[i for i,ok in enumerate(done) if not ok]})", file=sys.stderr)

    have = sum(os.path.exists(t[1]) for t in tasks)
    if have != n:
        sys.exit(f"only {have}/{n} frames on disk — refusing to write a short video")

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps),
                    "-i", os.path.join(tmp, "f%05d.png"),
                    "-r", "30", "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-an", a.out], check=True)
    size = os.path.getsize(a.out) // 1024
    print(f"  -> {a.out}  {size} kB  ({n} frames, conformed to 30fps CFR)")
    subprocess.run(["rm", "-rf", tmp])

if __name__ == "__main__":
    main()
