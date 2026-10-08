#!/usr/bin/env python3
"""
STEP ONE for any video the LIBRARY already covers — the block equivalent of source-scout.py.

    python scripts/build-block-picker.py work/nextphase/videos/<slug>/blocks.json      # per-beat, for approval
    python scripts/build-block-picker.py --all                          # every block, every mode

Written 2026-08-11 after ai-seems, where Jad had to say it twice:

  "no use the ui's that we have in our library man and show them to me"
  "why are you not using the ui of an actual claude code session???"

SOURCING.md 0b already said DO NOT FETCH for Claude Code / ChatGPT / sessions / skills — we own
those as blocks. The rule was there; what was missing was a step that makes you LOOK at the
blocks and put them in front of him before building. That is this.

Two things it exists to stop:

1. Going to the web for something we already own. The fix is to open this page first.
2. Assuming a block that is ADJACENT to the concept is the right block. `sessions-grid` draws
   generic terminal cards — it is NOT the Claude Code UI, and it was rejected on ai-seems for
   exactly that. If he names a product, the asset has to be recognisably THAT PRODUCT: its
   banner, its mark, its chrome. A bare prompt and a bar is not Claude ("use a, c doesn't look
   like a claude session").

Every candidate renders LIVE in an iframe. Never paste a still of a block into a review page —
a still goes stale and freezes whatever the plate looked like the day it was shot.

── blocks.json ───────────────────────────────────────────────────────────────
{
  "slug": "ai-seems",
  "serve": "http://127.0.0.1:8080",         optional, this is the default
  "beats": [
    {"id": "b1",
     "beat": "01 · HOOK",
     "at_video": "0.00-5.68",
     "line": "Your AI isn't getting dumber",
     "options": [
       {"url": "/ui-blocks/claude-new-chat.html?prompt=why%20do%20you...",
        "fit": "full",                      full | half | head — sets the preview aspect
        "why": "the real Claude composer, retyped to his own words"},
       {"img": "/ui/claude-code-window.png",
        "why": "a REAL Claude Code session — banner, model, cwd, live prompt"}
     ]}
  ]
}

`url` renders live in an iframe; `img` is for a real UI crop we already own on disk. Use `img`
only for genuine captures — anything that ANIMATES must be a url so he sees it move.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import argparse, html as H, json, pathlib, re, sys

REPO = pathlib.Path(__file__).resolve().parent.parent
BLOCKS = REPO / "ui-blocks"

ap = argparse.ArgumentParser()
ap.add_argument("spec", nargs="?", help="work/nextphase/videos/<slug>/blocks.json")
ap.add_argument("--all", action="store_true", help="every block x every documented mode")
ap.add_argument("--serve", default="http://127.0.0.1:8080")
a = ap.parse_args()

FITS = {"full": (1080, 1920, 0.278), "half": (1000, 880, 0.300), "head": (1000, 420, 0.300)}


def documented_modes(path):
    """Read the ?mode= / ?brand= options out of the block's own header comment. The header is
    the only place they are written down; parsing the JS would miss the ones behind a default."""
    head = path.read_text(errors="ignore")[:4000]
    modes = re.findall(r"\?mode=([a-z0-9-]+)", head)
    brands = re.findall(r"\?brand=([a-z0-9|]+)", head)
    for b in brands:
        modes += [f"brand={x}" for x in b.split("|")]
    seen, out = set(), []
    for m in modes:
        if m not in seen:
            seen.add(m); out.append(m)
    return out or [""]


def card(url=None, img=None, why="", fit="full", title=""):
    w, h, s = FITS.get(fit, FITS["full"])
    if img:
        media = (f'<div class="frame img" style="height:{round(h*s)}px">'
                 f'<img src="{H.escape(img)}" alt=""></div>')
    else:
        media = (f'<div class="frame" style="height:{round(h*s)}px">'
                 f'<iframe src="{H.escape(url)}" loading="lazy" '
                 f'style="width:{w}px;height:{h}px;transform:scale({s})"></iframe></div>')
    ref = H.escape(url or img)
    return f"""
      <div class="opt">
        <h3>{H.escape(title)}</h3>
        <code>{ref}</code>
        {media}
        <p class="why">{H.escape(why)}</p>
      </div>"""


CSS = """
  :root{--cream:#F0EDE4;--ink:#191817;--coral:#D97757;--soft:#6B6660;--card:#EAE6DA}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--cream);color:var(--ink);padding:44px 38px 120px;
       font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
  h1{font-size:32px;letter-spacing:-.02em;margin-bottom:6px}
  .sub{color:var(--soft);max-width:920px}
  .warn{background:#fff3cd;border-left:5px solid var(--coral);padding:14px 18px;
        margin:22px 0 30px;max-width:1000px;border-radius:0 8px 8px 0}
  .beat{margin:40px 0 0;padding-top:24px;border-top:2px solid rgba(0,0,0,.10)}
  .tag{display:inline-block;background:var(--ink);color:var(--cream);font-size:12px;
       font-weight:700;letter-spacing:.09em;padding:5px 11px;border-radius:4px;
       text-transform:uppercase}
  .line{font-size:21px;margin:11px 0 3px;max-width:1000px}
  .at{color:var(--soft);font-size:14px;font-variant-numeric:tabular-nums}
  .row{display:flex;gap:24px;flex-wrap:wrap;margin-top:18px}
  .opt{width:300px}
  .opt h3{font-size:15px;margin-bottom:3px}
  .opt code{font-size:11px;color:var(--soft);word-break:break-all;display:block;margin-bottom:8px}
  .frame{width:300px;overflow:hidden;background:#000;position:relative}
  .frame iframe{border:0;transform-origin:0 0;position:absolute;top:0;left:0}
  .frame.img{background:var(--card);display:flex;align-items:center}
  .frame.img img{width:100%;display:block}
  .why{font-size:14px;color:var(--soft);margin-top:8px}
"""

if a.all:
    rows = []
    for f in sorted(BLOCKS.glob("*.html")):
        opts = "".join(
            card(url=f"{a.serve}/ui-blocks/{f.name}"
                     + (f"?{m}" if m.startswith("brand=") else (f"?mode={m}" if m else "")),
                 why="", fit="full", title=(m or "default"))
            for m in documented_modes(f))
        rows.append(f'<div class="beat"><span class="tag">{H.escape(f.stem)}</span>'
                    f'<div class="row">{opts}</div></div>')
    body = "".join(rows)
    title = "every block, every documented mode"
    warn = ("This is the whole library, live. Open it BEFORE deciding a video needs anything "
            "fetched from the web.")
    out = REPO / "BLOCK-PICKER.html"
else:
    if not a.spec:
        sys.exit("give me a blocks.json, or --all")
    spec = json.loads(pathlib.Path(a.spec).read_text())
    serve = spec.get("serve", a.serve)
    rows = []
    for b in spec["beats"]:
        opts = "".join(
            card(url=(serve + o["url"]) if o.get("url") else None,
                 img=(serve + o["img"]) if o.get("img") else None,
                 why=o.get("why", ""), fit=o.get("fit", "full"),
                 title=o.get("title", ""))
            for o in b["options"])
        rows.append(
            f'<div class="beat"><span class="tag">{H.escape(b["beat"])}</span>'
            f'<p class="line">{H.escape(b.get("line",""))}</p>'
            f'<p class="at">{H.escape(str(b.get("at_video","")))}</p>'
            f'<div class="row">{opts}</div></div>')
    body = "".join(rows)
    title = f'{spec.get("slug","")} — pick the blocks'
    warn = ("Every option here is live, not a screenshot. Anything the library does not cover "
            "is called out per beat rather than padded with something adjacent.")
    out = pathlib.Path(a.spec).parent / "BLOCK-PICKER.html"

out.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><title>{H.escape(title)}</title>
<style>{CSS}</style></head><body>
<h1>{H.escape(title)}</h1>
<p class="sub">The real product UIs we already own, running live.</p>
<div class="warn">{H.escape(warn)}</div>
{body}
</body></html>""")
print(f"wrote {out}")
print("serve the repo root and open it:  python -m http.server 8080 --bind 127.0.0.1  (från skillmappen library/kits/nextphase/skills/nextphase-short-editing)")
