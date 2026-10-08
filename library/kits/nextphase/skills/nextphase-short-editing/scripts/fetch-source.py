#!/usr/bin/env python3
"""
Fetch real media from the web for a short, normalise it, and MAKE YOU LOOK AT IT.

    python scripts/fetch-source.py video  "<url>" out.mp4 --probe        # 4 stills across the clip
    python scripts/fetch-source.py video  "<url>" out.mp4 --at 3:12 --dur 5
    python scripts/fetch-source.py reddit "<permalink>" out.png
    python scripts/fetch-source.py x      "<status url>" out.png

Every clip comes back 30fps CFR (yt-dlp returns 24/25/50/60/VFR and those judder in a 30fps
composition) and with a contact sheet beside it, because the thing that disqualifies a clip —
a webcam bubble in the corner, another creator's captions, YouTube chrome — is only visible if
you look. See reference/SOURCING.md.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, json, pathlib, subprocess, sys, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("kind", choices=["video", "reddit", "x"])
ap.add_argument("url")
ap.add_argument("out")
ap.add_argument("--at",   default=None, help="start timecode, e.g. 3:12")
ap.add_argument("--dur",  type=float, default=5.0)
ap.add_argument("--probe", action="store_true",
                help="grab 2s at four points across the clip so you can pick before committing")
a = ap.parse_args()

out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def secs(tc):
    if tc is None: return 0
    parts = [float(x) for x in str(tc).split(":")]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))

def contact_sheet(mp4, sheet, n=6):
    """The step people skip. A webcam bubble is obvious in six frames and invisible in none."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(mp4)],
                               capture_output=True, text=True).stdout.strip() or 0)
    if dur <= 0:
        return
    tiles = []
    tmp = mp4.parent / "_probe"
    tmp.mkdir(exist_ok=True)
    for i in range(n):
        t = dur * (i + 0.5) / n
        f = tmp / f"t{i}.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(mp4),
             "-frames:v", "1", "-vf", "scale=360:-1", str(f)])
        tiles.append(f)
    run(["ffmpeg", "-v", "error", "-y", *sum([["-i", str(t)] for t in tiles], []),
         "-filter_complex", f"hstack={len(tiles)}", str(sheet)])
    for t in tiles: t.unlink()
    tmp.rmdir()

# ── video ────────────────────────────────────────────────────────────────────
if a.kind == "video":
    if a.probe:
        print("probing four points — look at each before you commit to one")
        dur_s = subprocess.run(["yt-dlp", "--no-warnings", "--print", "duration", a.url],
                               capture_output=True, text=True).stdout.strip()
        total = float(dur_s or 60)
        for i, frac in enumerate([0.15, 0.35, 0.6, 0.85]):
            t = total * frac
            p = out.with_name(f"{out.stem}-probe{i}.mp4")
            run(["yt-dlp", "--no-warnings", "-q", "-f", "mp4",
                 "--download-sections", f"*{t:.0f}-{t+2:.0f}", "--force-keyframes-at-cuts",
                 "-o", str(p), a.url])
            print(f"  {p.name}  @ {t/60:.0f}:{t%60:02.0f}")
        print("\npick one, then re-run with --at <timecode> --dur <seconds>")
        sys.exit(0)

    start = secs(a.at)
    raw = out.with_name(out.stem + "-raw.mp4")
    run(["yt-dlp", "--no-warnings", "-q", "-f", "mp4",
         "--download-sections", f"*{start:.0f}-{start + a.dur:.0f}",
         "--force-keyframes-at-cuts", "-o", str(raw), a.url])
    # 30fps CFR or it drifts off the beat it was cut to
    run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-r", "30", "-fps_mode", "cfr",
         "-an", "-c:v", "libx264", "-crf", "21", "-pix_fmt", "yuv420p", str(out)])
    raw.unlink(missing_ok=True)
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height,r_frame_rate",
                           "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    sheet = out.with_name(out.stem + "-CHECK.png")
    contact_sheet(out, sheet)
    print(f"\n{out}   {info}")
    print(f"{sheet}")
    print("\n⚠ LOOK AT THE CONTACT SHEET before using this. Reject it if you see:")
    print("   a webcam bubble in a corner · another creator's captions · a cursor trail")
    print("   · YouTube chrome · UI too small to read at 9:16   (reference/SOURCING.md)")

# ── reddit / x — the POST, shot 9:16 ─────────────────────────────────────────
else:
    if a.kind == "reddit":
        # the .json endpoint is the honest way to read a thread, and it needs no scraping
        # reddit 403s a generic UA; old.reddit is the reliable read path
        js = a.url.rstrip("/").replace("://www.", "://old.") + ".json"
        req = urllib.request.Request(js, headers={
            "User-Agent": "content-engine-nextphase/1.0 (privat research-skript; ingen förklädnad)"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=20).read())
            post = d[0]["data"]["children"][0]["data"]
            print(f"  r/{post['subreddit']} · {post['ups']} upvotes · {post['num_comments']} comments")
            print(f"  “{post['title']}”")
            if post.get("is_video"):
                print("  NOTE: this post has a video. Prefer the POST over lifting the video —"
                      " see SOURCING.md §3 (rights).")
        except Exception as e:
            print(f"  (could not read the json endpoint: {e})", file=sys.stderr)

    print("\nNOTE: reddit and x block headless Chromium — both serve a bot wall with HTTP 200.")
    print("      If this refuses, drive the real logged-in browser instead (Claude in Chrome)")
    print("      and screenshot the post from there. See reference/SOURCING.md §2b.\n")
    here = pathlib.Path(__file__).parent
    print("shooting the post as a 9:16 frame …")
    run([sys.executable, str(here / "shoot-page-9x16.py"), a.url, str(out),
         "--w", "560", "--dpr", "3"])
    print("\n⚠ Check the shot: no cookie wall, no login overlay, and the post readable at 9:16.")
