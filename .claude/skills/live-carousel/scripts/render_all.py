#!/usr/bin/env python3
"""Audio -> build -> check -> render every slide -> verify -> contact sheet + seam strips + swipe preview.

  py render_all.py [name | project-dir] [--only 01-hook 03-weight] [--workers 2] [--quality looks]
                   [--no-audio] [--no-check] [--check-only] [--open]

A bare name means <repo>/work/live-carousel/<name>. Outputs, all inside the project:
  renders/slide-<name>.mp4     one 1080x1350 30 fps MP4 per slide, sound included (what you post)
  renders/contact-sheet.jpg    top row = frame 0 of every slide, bottom row = mid-slide
  renders/seams/<name>.jpg     last frame | first frame, to eyeball the loop seam
  preview.html                 local Instagram-style swipe preview of the renders (--open opens it)

Windows port: npx is resolved to npx.cmd, all text I/O is UTF-8, and the HyperFrames CLI is the one already
installed (`npx hyperframes`; pin with LIVE_CAROUSEL_HF=hyperframes@<version>).
"""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
REPO = SKILL.parent.parent.parent
WORK = REPO / "work" / "live-carousel"
HF = os.environ.get("LIVE_CAROUSEL_HF", "hyperframes")
NPX = shutil.which("npx") or "npx"  # npx.cmd on Windows

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def project_dir(arg):
    if not any(sep in arg for sep in ("/", "\\")) and not Path(arg).is_absolute() and arg not in (".", ".."):
        return (WORK / arg).resolve()
    return Path(arg).expanduser().resolve()


def run(cmd, cwd, quiet=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not quiet or r.returncode:
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if out:
            print("\n".join("    " + line for line in out.splitlines()[-40:]))
    return r.returncode


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
    )
    d = json.loads(r.stdout or "{}")
    kinds = [s.get("codec_type") for s in d.get("streams", [])]
    return float(d.get("format", {}).get("duration", 0)), "audio" in kinds


def frame(src, t, out, w=360):
    """Grab one frame at t seconds; t=None grabs the very last frame."""
    seek = ["-sseof", "-0.3"] if t is None else ["-ss", f"{max(0, t):.3f}"]
    tail = ["-update", "1"] if t is None else ["-frames:v", "1"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *seek, "-i", str(src), *tail, "-vf", f"scale={w}:-2", str(out)], check=True)


def stack(images, out, layout):
    args = ["ffmpeg", "-v", "error", "-y"]
    for im in images:
        args += ["-i", str(im)]
    args += ["-filter_complex", layout, "-q:v", "3", str(out)]
    subprocess.run(args, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--workers", default="2")
    ap.add_argument("--quality", default="looks")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--check-only", action="store_true", help="build and check, no render")
    ap.add_argument("--browser-gpu", action="store_true", help="pass --browser-gpu to the renderer (WebGL sky)")
    ap.add_argument("--open", action="store_true", help="open preview.html when done")
    a = ap.parse_args()

    proj = project_dir(a.project)
    cfg_path = proj / "carousel.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig")) if cfg_path.exists() else {}
    slides = cfg.get("slides") or sorted(p.stem for p in (proj / "src").glob("*.html") if not p.stem.startswith("_"))
    todo = [s for s in slides if not a.only or s in a.only]
    py = sys.executable
    t_all = time.time()

    if not a.no_audio and (proj / "audio/make_audio.py").exists():
        print("» audio")
        if run([py, "make_audio.py"], proj / "audio"):
            sys.exit("audio/make_audio.py failed")
    print("» build")
    if run([py, "build.py", *todo], proj):
        sys.exit("build.py failed")

    if not a.no_check:
        failed = []
        for s in todo:
            print(f"» check {s}")
            if run([NPX, "--yes", HF, "check"], proj / "slides" / s, quiet=True):
                failed.append(s)
        if failed:
            sys.exit(f"check failed for: {', '.join(failed)}. Fix the errors above, then run again.")
    if a.check_only:
        print("checks passed")
        return

    renders = proj / "renders"
    (renders / "seams").mkdir(parents=True, exist_ok=True)
    frames = renders / ".frames"
    frames.mkdir(exist_ok=True)
    timings = {}
    for s in todo:
        out = renders / f"slide-{s}.mp4"
        print(f"» render {s}", flush=True)
        t0 = time.time()
        cmd = [NPX, "--yes", HF, "render", "-o", str(out), "--workers", str(a.workers), "--quality", a.quality, "--quiet"]
        if a.browser_gpu:
            cmd.append("--browser-gpu")
        code = run(cmd, proj / "slides" / s, quiet=True)
        timings[s] = time.time() - t0
        print(f"    {timings[s]:.0f}s", flush=True)
        if code or not out.exists():
            sys.exit(f"render failed for {s}")

    print("» verify")
    ok_all = True
    for s in slides:
        out = renders / f"slide-{s}.mp4"
        if not out.exists():
            continue
        dur, has_audio = probe(out)
        flag = "" if has_audio else "   <- NO AUDIO"
        ok_all &= has_audio
        print(f"    slide-{s}.mp4  {dur:.2f}s  {out.stat().st_size / 1e6:.1f} MB{flag}")
        frame(out, 0, frames / f"{s}-first.png")
        frame(out, dur * 0.45, frames / f"{s}-mid.png")
        frame(out, None, frames / f"{s}-last.png")
        stack([frames / f"{s}-last.png", frames / f"{s}-first.png"], renders / "seams" / f"{s}.jpg", "[0][1]hstack=inputs=2")

    done = [s for s in slides if (renders / f"slide-{s}.mp4").exists()]
    if done:
        firsts = [frames / f"{s}-first.png" for s in done]
        mids = [frames / f"{s}-mid.png" for s in done]
        n = len(done)
        if n == 1:
            layout = "[0][1]vstack=inputs=2"
        else:
            top = "".join(f"[{i}]" for i in range(n)) + f"hstack=inputs={n}[t];"
            bot = "".join(f"[{n + i}]" for i in range(n)) + f"hstack=inputs={n}[b];"
            layout = top + bot + "[t][b]vstack=inputs=2"
        stack(firsts + mids, renders / "contact-sheet.jpg", layout)

        tpl = proj / ".preview.template.html"
        if tpl.exists():
            esc = html.escape
            vids = "\n".join(
                f'          <video src="renders/slide-{s}.mp4" playsinline loop muted preload="auto"></video>' for s in done
            )
            dots = "".join('<i class="on"></i>' if i == 0 else "<i></i>" for i in range(n))
            page = (
                tpl.read_text(encoding="utf-8")
                .replace("<!--@VIDEOS@-->", vids)
                .replace("<!--@DOTS@-->", dots)
                .replace("@N@", str(n))
                .replace("@TITLE@", esc(cfg.get("title", "Live carousel")))
                .replace("@HANDLE@", esc(cfg.get("handle", "your_handle")))
                .replace("@CAPTION@", esc(cfg.get("caption", "")))
            )
            (proj / "preview.html").write_text(page, encoding="utf-8")
    print()
    if timings:
        print("render times:   " + ", ".join(f"{k} {v:.0f}s" for k, v in timings.items()) + f"  (total {time.time() - t_all:.0f}s)")
    print(f"renders:        {renders}")
    print(f"contact sheet:  {renders / 'contact-sheet.jpg'}")
    print(f"loop seams:     {renders / 'seams'}")
    if (proj / "preview.html").exists():
        print(f"swipe preview:  {proj / 'preview.html'}")
        if a.open and hasattr(os, "startfile"):
            os.startfile(proj / "preview.html")  # Windows `start`
    if not ok_all:
        sys.exit("some renders have no audio track: check audio/out/ and the <audio> element in the slide")


if __name__ == "__main__":
    main()
