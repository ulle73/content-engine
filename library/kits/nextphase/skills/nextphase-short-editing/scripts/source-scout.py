#!/usr/bin/env python3
"""
STEP ZERO of every edit: find the real media FIRST, and put it in front of Jad before a single
beat is built — FOUR options per beat, one from each source, each labelled with where it came
from.

    python scripts/source-scout.py work/nextphase/videos/<slug>/scout.json
    python scripts/source-scout.py work/nextphase/videos/<slug>/scout.json --only b1        # re-scout one beat
    python scripts/source-scout.py work/nextphase/videos/<slug>/scout.json --only b1:x      # one option

Jad, 2026-08-10:

  "it has to be four videos and each one has to be like, oh you got them from YouTube, you got
   them from Reddit, you got them from Twitter — give me the resource where you got it from, or
   you got it from Google."

So every beat that wants real media gets a row of FOUR candidates:

    youtube · reddit · x · web        (web = a real page, found via search)

Each card carries the source badge, the full URL it came from, and the beat / line / slot it is
proposed for. He picks per beat. Rejected → scout that beat again with different candidates.

── scout.json ────────────────────────────────────────────────────────────────
{
  "slug": "tp-0811",
  "script": "one line on what the video is about",
  "beats": [
    {"id": "b1",
     "beat": "01 · HOOK",
     "at_video": "0.00-4.40",
     "slot": "above his head (transparent)",
     "line": "Your Claude Code session can now talk to each other",
     "options": [
       {"source": "youtube", "url": "https://www.youtube.com/watch?v=...", "at": "12:55",
        "dur": 6, "why": "the feature actually running, no webcam"},
       {"source": "reddit",  "url": "https://www.reddit.com/r/.../comments/...",
        "hl": "a sentence to mark", "why": "real people reacting; the title IS the hook"},
       {"source": "x",       "url": "https://x.com/user/status/...", "why": "the announcement"},
       {"source": "web",     "url": "https://...", "hl": "a sentence to mark",
        "why": "the authoritative claim"}
     ]}
  ]
}

Clips come back 30fps CFR at >=1080p. Pages come back as true 9:16 frames at 420 CSS px so the
type scales ~2.6x UP rather than reading as small text.

⚠ Reddit and X serve a bot wall to headless Chromium with HTTP 200 — a perfectly valid
screenshot of nothing. shoot-page-9x16.py refuses to write one, and the card is marked BLOCKED
so it is obvious the route is "drive Jad's own logged-in browser", not "ship the wall".
See reference/SOURCING.md §2b.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import sys
import argparse, datetime, html as H, json, pathlib, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("spec")
ap.add_argument("--only", default=None, help="beat ids, or beat:source, comma separated")
ap.add_argument("--keep", action="store_true", help="skip anything already downloaded")
a = ap.parse_args()

SPEC = pathlib.Path(a.spec).resolve()
VID  = SPEC.parent
spec = json.loads(SPEC.read_text())
SLUG = spec.get("slug", VID.name)
OUT  = VID / "assets" / "broll" / "candidates"
OUT.mkdir(parents=True, exist_ok=True)
REPO = pathlib.Path(__file__).resolve().parent.parent

BADGE = {"youtube": ("YouTube", "#FF0033"), "reddit": ("Reddit", "#FF4500"),
         "x": ("X / Twitter", "#111111"), "web": ("Google / web", "#1A73E8")}

only = {}
if a.only:
    for tok in a.only.split(","):
        b, _, s = tok.partition(":")
        only.setdefault(b, set())
        if s:
            only[b].add(s)


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def vprobe(p):
    o = sh(["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-show_entries", "format=duration", "-of", "json", str(p)]).stdout
    try:
        d = json.loads(o); st = d["streams"][0]
        n, dn = st["r_frame_rate"].split("/")
        return int(st["width"]), int(st["height"]), round(int(n)/max(int(dn), 1), 2), \
            float(d["format"]["duration"])
    except Exception:
        return 0, 0, 0, 0.0


def get_video(key, o):
    """A window of real footage, >=1080p, conformed to 30fps CFR."""
    dst = OUT / f"{key}.mp4"
    if dst.exists() and a.keep:
        return dst, ""
    # A direct media URL (a vendor CDN mp4) is a plain download — yt-dlp is for extractor sites
    # and mangles a bare file. Still conform it to 30fps CFR like everything else.
    if o["url"].split("?")[0].lower().endswith((".mp4", ".webm", ".mov")):
        raw = OUT / f"_{key}_direct.mp4"
        sh(["curl", "-sL", o["url"], "-o", str(raw)])
        if raw.exists() and raw.stat().st_size > 0:
            sh(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-vf", "fps=30",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", str(dst)])
            raw.unlink(missing_ok=True)
        if not dst.exists():
            return None, "COULD NOT FETCH — direct download failed"
        w, h, fps, dur = vprobe(dst)
        return dst, f"{w}x{h} · {fps:g}fps · {dur:.1f}s"

    parts = [float(x) for x in str(o.get("at", "0:00")).split(":")]
    start = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
    end = start + float(o.get("dur", 6))
    raw = OUT / f"_{key}.%(ext)s"
    got = []
    for fmt in ["bestvideo[height>=1080]+bestaudio/best[height>=1080]", "bestvideo+bestaudio/best"]:
        sh(["yt-dlp", "-f", fmt, "--download-sections", f"*{start}-{end}",
            "--force-keyframes-at-cuts", "-o", str(raw), "--no-playlist", o["url"]])
        got = sorted(OUT.glob(f"_{key}.*"))
        if got:
            break
    if not got:
        return None, "COULD NOT FETCH — host refused, or the format is gone"
    sh(["ffmpeg", "-v", "error", "-y", "-i", str(got[0]), "-vf", "fps=30", "-an",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(dst)])
    for g in got:
        g.unlink(missing_ok=True)
    if not dst.exists():
        return None, "COULD NOT TRANSCODE"
    w, h, fps, dur = vprobe(dst)
    note = f"{w}x{h} · {fps:g}fps · {dur:.1f}s"
    if w and w < 1600:
        note = f"⚠ only {w}x{h} — UI likely unreadable once scaled into a 9:16 slot"
    return dst, note


def get_page(key, o):
    """A real page as a true 9:16 frame, type scaled ~2.6x UP (420 CSS px)."""
    dst = OUT / f"{key}.png"
    if dst.exists() and a.keep:
        return dst, ""
    cmd = [sys.executable, str(REPO / "scripts" / "shoot-page-9x16.py"), o["url"], str(dst),
           "--w", "420", "--dpr", "3"]
    for phrase in ([o["hl"]] if isinstance(o.get("hl"), str) else o.get("hl", [])):
        cmd += ["--hl", phrase]
    r = sh(cmd)
    if dst.exists():
        last = (r.stdout.strip().splitlines() or [""])[-1]
        # A shot that found NONE of its phrases usually means the content never rendered —
        # a forum thread came back as the site's footer icons and still wrote a valid PNG.
        # Flag it rather than let a junk frame sit on the page looking like a candidate.
        asked = 1 if isinstance(o.get("hl"), str) else len(o.get("hl", []))
        if asked and " 0 phrase(s)" in last:
            return dst, ("⚠ NONE of the marked text was found on the page — the content probably "
                         "did not render (JS wall, login, or a redirect). Look before trusting it.")
        return dst, last
    rej = dst.with_suffix("").with_suffix(".REJECTED.png")
    blocked = rej.exists() or "wall" in (r.stdout + r.stderr).lower()
    if blocked and o.get("source") in ("reddit", "x"):
        return (rej if rej.exists() else None), \
            "BLOCKED — served a bot wall to headless Chromium. Needs your logged-in browser."
    return None, "COULD NOT SHOOT — " + (r.stderr.strip().splitlines() or ["unknown"])[-1][:120]


def sheet(mp4, out, n=6):
    w, h, fps, dur = vprobe(mp4)
    if dur <= 0:
        return None
    tmp = out.parent / f"_s{out.stem}"
    tmp.mkdir(exist_ok=True)
    got = 0
    for i in range(n):
        f = tmp / f"{i}.png"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur*(i+0.5)/n:.2f}", "-i", str(mp4),
            "-frames:v", "1", "-vf", "scale=420:-1", str(f)])
        got += f.exists()
    if got:
        sh(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "%d.png"),
            "-filter_complex", f"tile=3x{(got+2)//3}", str(out)])
    for f in tmp.glob("*.png"):
        f.unlink()
    tmp.rmdir()
    return out if out.exists() else None


cards = []
for b in spec["beats"]:
    if only and b["id"] not in only:
        continue
    want = only.get(b["id"], set())
    opts = []
    for o in b["options"]:
        src = o.get("source", "web")
        if want and src not in want:
            continue
        # index the key: a beat may legitimately carry two options from one source
        # (e.g. two different vendor pages), and {beat}-{source} collided so the
        # second silently overwrote the first.
        key = f"{b['id']}-{src}-{len(opts)+1}"
        print(f"  {b['id']:<4} {src:<8} {o.get('url','(no source)')[:70]}")
        if o.get("unavailable"):
            print(f"        -> GAP: {o['unavailable']}")
            opts.append((src, o, None, "none", "NO SOURCE EXISTS — " + o["unavailable"], key))
            continue
        # Real footage does not only come from YouTube. A vendor's own launch post often serves
        # the clips straight off its CDN (minimax.io did), and those are the BEST source there
        # is — the thing itself, no chrome, no webcam bubble possible. Mark those {"kind":
        # "video"} and they get a player instead of being shot as a page.
        if src == "youtube" or o.get("kind") == "video":
            path, note = get_video(key, o)
            kind = "video"
            if path:
                sheet(path, OUT / f"{key}-sheet.jpg")
        else:
            path, note = get_page(key, {**o, "source": src})
            kind = "image"
        print(f"        -> {note or 'ok'}")
        opts.append((src, o, path, kind, note, key))
    cards.append((b, opts))

STAMP = datetime.date.today().isoformat()


def opt_html(b, src, o, path, kind, note, key=None):
    label, colour = BADGE.get(src, (src, "#666"))
    bad = (path is None) or note.startswith(("⚠", "COULD", "BLOCKED"))
    if path is None:
        media = '<div class="missing">nothing usable came back</div>'
    elif kind == "video":
        media = (f'<video src="assets/broll/candidates/{path.name}" controls loop muted '
                 f'playsinline></video>')
        s = OUT / f"{key}-sheet.jpg"
        if s.exists():
            media += f'<img class="sheet" src="assets/broll/candidates/{s.name}" alt="">'
    else:
        media = f'<img class="shot" src="assets/broll/candidates/{path.name}" alt="">'
    return f"""
    <div class="opt {'bad' if bad else ''}">
      <div class="badge" style="background:{colour}">{H.escape(label)}</div>
      {media}
      <p class="why">{H.escape(o.get('why',''))}</p>
      <p class="src"><b>Source</b><br>{f'<a href="{H.escape(o["url"])}" target="_blank">{H.escape(o["url"])}</a>' if o.get('url') else '<i>nothing to link — this slot is empty</i>'}
         {('&nbsp;@&nbsp;'+H.escape(str(o['at']))) if o.get('at') else ''}<br>
         <span class="stamp">fetched {STAMP}</span></p>
      <p class="note {'bad' if bad else ''}">{H.escape(note)}</p>
    </div>"""


BEATS = "\n".join(f"""
<section class="beat">
  <header>
    <span class="bid">{H.escape(b['id'])}</span>
    <span class="bname">{H.escape(b.get('beat',''))}</span>
    <span class="where">{H.escape(b.get('at_video',''))} &middot; {H.escape(b.get('slot',''))}</span>
  </header>
  <p class="line">&ldquo;{H.escape(b.get('line',''))}&rdquo;</p>
  <div class="opts">{''.join(opt_html(b,*o) for o in opts)}</div>
</section>""" for b, opts in cards)

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><title>{H.escape(SLUG)} — media to approve</title>
<style>
  :root{{--cream:#F0EDE4;--coral:#D97757;--ink:#191817;--soft:#6B6660}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--cream);color:var(--ink);
    font:16px/1.5 -apple-system,Inter,sans-serif;padding:40px}}
  h1{{font-size:40px;margin:0 0 6px;letter-spacing:-.02em}}
  .sub{{color:var(--soft);margin:0 0 36px;max-width:78ch}}
  .beat{{background:#fff;border-radius:20px;padding:26px;margin-bottom:30px}}
  header{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
  .bid{{background:var(--ink);color:#fff;font-weight:800;padding:4px 12px;border-radius:8px}}
  .bname{{font-weight:800;font-size:20px;letter-spacing:.01em}}
  .where{{color:var(--soft);font-size:14px}}
  .line{{font-size:22px;font-style:italic;margin:.5em 0 1.2em;color:#33302c}}
  .opts{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}}
  @media(max-width:1400px){{.opts{{grid-template-columns:repeat(2,1fr)}}}}
  .opt{{border:2px solid #E7E3D9;border-radius:14px;padding:14px;display:flex;flex-direction:column}}
  .opt.bad{{border-color:#E8C0BA;background:#FFF7F6}}
  .badge{{align-self:flex-start;color:#fff;font-weight:800;font-size:12px;letter-spacing:.06em;
    text-transform:uppercase;padding:4px 10px;border-radius:6px;margin-bottom:10px}}
  video,.shot{{width:100%;border-radius:10px;display:block;background:#000}}
  .shot{{background:#fff;max-height:420px;object-fit:cover;object-position:top}}
  .sheet{{width:100%;margin-top:8px;border-radius:8px;display:block}}
  .missing{{padding:40px 10px;text-align:center;color:#B3261E;font-weight:700;
    border:2px dashed #E8C0BA;border-radius:10px}}
  .why{{margin:10px 0 8px;font-size:15px}}
  .src{{margin:0 0 8px;font-size:12px;color:var(--soft);word-break:break-all}}
  .src b{{color:var(--ink);font-size:11px;letter-spacing:.05em;text-transform:uppercase}}
  .stamp{{opacity:.7}}
  .note{{margin:auto 0 0;font-size:13px;color:var(--soft)}}
  .note.bad{{color:#B3261E;font-weight:700}}
  a{{color:var(--coral)}}
</style></head><body>
<h1>{H.escape(SLUG)} — media to approve</h1>
<p class="sub">{H.escape(spec.get('script',''))}<br>
Four options per beat, one per source. Nothing is cut in yet — tell me which one you want for
each beat, and I'll go find new options for any beat you don't like.</p>
{BEATS}
</body></html>"""

(VID / "SOURCING.html").write_text(page)
print(f"\nwrote {VID/'SOURCING.html'} — {len(cards)} beat(s), "
      f"{sum(len(o) for _, o in cards)} option(s)")
