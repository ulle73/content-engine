#!/usr/bin/env python3
"""
MOTION STRIPS — the shelf, but showing what each animation DOES.

    python scripts/build-motion-strips.py            # rebuild strips + sheets
    python scripts/build-motion-strips.py --open

Written 2026-08-21, after Jad rejected tp-0821's first cut:

    "this is really bad, most of the video is just screenshots of text, I need animations
     bro, we have literally an entire library"

`shelf/` already exists and is correct, and it is **one frame per item**. A still of an
animation tells you what it looks like, never what it does — so every registry item reads as
a static card and a real screenshot always looks like the stronger pick. `scroll-feed` is a
blank wall as a still and a river of records in motion. `split-tilt-cards` is two grey
rectangles until you watch BEFORE turn into AFTER.

So: four frames across every preview, hstacked into a strip, 25 strips to a sheet. Eight
images instead of an hour of scrubbing. `strips/order.txt` carries the reading order, since
burning names in needs a fontconfig this environment does not have.

Only `on-brand` and `needs-work` items appear — `off-palette` is quarantined and
`captured-device` only belongs when the subject genuinely IS that device.

⭐ AND THEN PROBE BEFORE YOU BUILD. These components size everything off `cqmin` of the box
you mount them in, so a pick that is perfect full-frame can be unreadable in a 1000x880 half.
Mount your shortlist at the boxes they will actually get and render 3s each — 13 candidates
took 20 seconds and killed four of them before they cost a render. See the memory
`registry-type-is-cqmin`.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, json, pathlib, subprocess, sys, webbrowser
import concurrent.futures as cf

def _find_repo():
    """Walk up until broll-library/ turns up, so this works whether the script sits at the
    project root or inside the skill package."""
    here = pathlib.Path(__file__).resolve()
    for d in here.parents:
        if (d / "broll-library").is_dir():
            return d
    return here.parent.parent


REPO = _find_repo()
PREV = REPO / "broll-library" / "registry" / "previews"
GRADE = REPO / "broll-library" / "registry" / "brand-grade.json"
OUT = REPO / "strips"
FRAMES, FW, FH, PER_SHEET, COLS = 4, 150, 266, 25, 5

ap = argparse.ArgumentParser()
ap.add_argument("--open", action="store_true")
ap.add_argument("--jobs", type=int, default=8)
a = ap.parse_args()

OUT.mkdir(exist_ok=True)
grade = json.loads(GRADE.read_text())
usable = [p for p in sorted(PREV.glob("*.mp4"))
          if grade.get(p.stem, {}).get("grade") in ("on-brand", "needs-work")]
if not usable:
    sys.exit("no usable previews — run scripts/render-registry-previews.py first")


def strip(p):
    out = OUT / f"{p.stem}.png"
    if out.exists() and out.stat().st_size > 2000:
        return p.stem
    try:
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip())
    except Exception:
        return None
    parts = []
    for i, f in enumerate((0.12, 0.38, 0.64, 0.90)):
        fp = OUT / f"_{p.stem}_{i}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{dur*f:.2f}", "-i", str(p),
                        "-frames:v", "1", "-vf", f"scale={FW}:{FH}", str(fp)], check=False)
        if fp.exists():
            parts.append(fp)
    if len(parts) < FRAMES:
        for f in parts:
            f.unlink(missing_ok=True)
        return None
    subprocess.run(["ffmpeg", "-y", "-v", "error", *sum([["-i", str(f)] for f in parts], []),
                    "-filter_complex", f"[0][1][2][3]hstack={FRAMES}",
                    "-frames:v", "1", str(out)], check=False)
    for f in parts:
        f.unlink(missing_ok=True)
    return p.stem


with cf.ThreadPoolExecutor(a.jobs) as ex:
    names = sorted(n for n in ex.map(strip, usable) if n)
(OUT / "order.txt").write_text("\n".join(names))

sheets = []
for s in range(0, len(names), PER_SHEET):
    chunk = names[s:s + PER_SHEET]
    ins = sum([["-i", str(OUT / f"{n}.png")] for n in chunk], [])
    lay = []
    for i in range(len(chunk)):
        c, r = i % COLS, i // COLS
        x = "0" if c == 0 else "+".join(f"w{k}" for k in range(c))
        y = "0" if r == 0 else "+".join(f"h{k*COLS}" for k in range(r))
        lay.append(f"{x}_{y}")
    fc = "".join(f"[{i}]" for i in range(len(chunk))) + \
         f"xstack=inputs={len(chunk)}:layout=" + "|".join(lay)
    name = f"strips-{s//PER_SHEET + 1}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc,
                    "-frames:v", "1", str(OUT / name)], check=True)
    sheets.append((name, chunk))

rows = "\n".join(
    f'<section><h2>{n}</h2><p class="names">{" · ".join(c)}</p>'
    f'<img src="{n}" alt=""></section>' for n, c in sheets)
(OUT / "STRIPS.html").write_text(f"""<!doctype html><meta charset="utf-8">
<title>Motion strips — {len(names)} animations</title>
<style>
 body{{margin:0;background:#141414;color:#EDE7DC;font:15px/1.5 ui-sans-serif,system-ui}}
 header{{padding:28px 32px 10px}} h1{{margin:0;font-size:26px}}
 p.lead{{margin:6px 0 0;color:#9C948A;max-width:70ch}}
 section{{padding:22px 32px}} h2{{margin:0 0 4px;font-size:15px;color:#8FE38F}}
 p.names{{margin:0 0 10px;color:#9C948A;font-size:12px}}
 img{{width:100%;display:block;image-rendering:crisp-edges}}
</style>
<header><h1>Motion strips — {len(names)} animations</h1>
<p class="lead">Four frames across every registry preview, left to right. The shelf shows one
frame per item, which tells you what an animation looks like and never what it does — this
page is the same library, moving. Names run in reading order under each sheet.</p></header>
{rows}""")

print(f"{len(names)} strips · {len(sheets)} sheets -> {OUT}/STRIPS.html")
if a.open:
    webbrowser.open((OUT / "STRIPS.html").as_uri())
