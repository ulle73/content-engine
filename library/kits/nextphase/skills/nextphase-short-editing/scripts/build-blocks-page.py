#!/usr/bin/env python3
"""
BLOCKS.html — every animated block in the library, LIVE, old and new.

    python scripts/build-blocks-page.py

Why live iframes and not stills: a still of an animated block is the single most common
complaint, and a stale still also freezes whatever the plate looked like the day it was shot —
which is how the retired graph-paper grid was still on screen weeks after it was killed. An
iframe always shows the block as it is now.
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import html, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# name, variants [(label, query)], slot (w,h), one line on what it is for
BLOCKS = [
 ("sessions-grid.html", "NEW", [
     ("babysit — 4 sessions, 3 stalled, mascot running between them", "?mode=babysit"),
     ("parallel — all four running on their own", "?mode=parallel"),
     ("approve — a message arrives, Allow / Deny", "?mode=approve"),
     ("babysit, coral half", "?mode=babysit&fit=half&plate=none"),
   ], "Real session windows. Use this whenever the line is about sessions — the SESSIONS are the "
      "UI and the mascot is only what tends them."),
 ("page-highlight.html", "NEW", [
     ("b-roll full — the page owns the frame, push into the mark", "?src=pages/example-page.png&fit=full&zoom=in"),
     ("split — marker band in the top half", "?src=pages/example-page.png&fit=half&zoom=out"),
     ("transparent — a card above his head", "?src=pages/example-page.png&fit=head&zoom=hold"),
   ], "A real page as a true 9:16 frame with the marker on the real words. One mark at a time. "
      "Shoot the page with scripts/shoot-page-9x16.py."),
 ("sessions-hub.html", "", [
     ("talk — one session messages another", "?mode=talk"),
     ("hub — one conducting mac mini / laptop / desktop", "?mode=hub"),
     ("solo — waiting on the first one", "?mode=solo"),
   ], "Mascots as the endpoints of a wire. Good for machines and hand-offs — but when the line "
      "is about SESSIONS, use sessions-grid instead."),
 ("ai-new-chat.html", "", [
     ("claude", "?brand=claude&seek=5.2"), ("chatgpt", "?brand=chatgpt&seek=5.2"),
     ("gemini", "?brand=gemini&seek=5.2"), ("grok", "?brand=grok&seek=5.2"),
     ("perplexity", "?brand=perplexity&seek=5.2"),
   ], "Every assistant's new-chat screen through the SAME three-phase camera move, so cutting "
      "between two reads as one system. The composer always comes with its lockup."),
 ("skills-beat.html", "", [("slash menu", "?mode=slash&seek=4.0"), ("default", "?seek=4.0")],
     "The skills surface — the slash-command menu."),
 ("skill-folder.html", "", [("the folder fan", "?seek=3.0")],
     "Apple's file fan: files lift out of the mouth on their own arcs, fan, hold, drop back."),
 ("claude-new-chat.html", "", [("default", "")],
     "The Claude new-chat screen rebuilt as DOM, so the camera can move through it."),
 ("article-highlight.html", "RETIRED", [("the original technique", "")],
     "SUPERSEDED by page-highlight.html — hardcoded screenshot, rects nudged by eye, browser "
     "chrome, and five marks at once. Kept only as the record."),
]

MASCOTS = sorted((ROOT / "mascot/outline").glob("*.webp"))

cards = []
for fname, badge, variants, why in BLOCKS:
    if not (ROOT / "ui-blocks" / fname).exists():
        continue
    tiles = []
    for label, q in variants:
        fit = "half" if "fit=half" in q else "head" if "fit=head" in q else "full"
        W, H = {"full": (1080, 1920), "half": (1000, 880), "head": (1000, 620)}[fit]
        tiles.append(f'''<figure class="v">
          <div class="fh" style="aspect-ratio:{W}/{H}">
            <iframe src="ui-blocks/{fname}{html.escape(q)}" loading="lazy"
                    scrolling="no" tabindex="-1" style="width:{W}px;height:{H}px"></iframe>
          </div>
          <figcaption>{html.escape(label)}
            <a href="ui-blocks/{fname}{html.escape(q)}" target="_blank">open ↗</a>
          </figcaption></figure>''')
    b = f'<span class="badge b-{badge.lower()}">{badge}</span>' if badge else ""
    cards.append(f'''<section class="blk">
      <div class="bh"><h2>{fname.replace(".html","")}</h2>{b}
        <span class="cnt">{len(variants)} variant{"s" if len(variants)!=1 else ""}</span></div>
      <p class="why">{html.escape(why)}</p>
      <div class="vs">{"".join(tiles)}</div>
    </section>''')

masc = "".join(
    f'<figure class="m"><img src="mascot/outline/{m.name}" loading="lazy" alt="">'
    f'<figcaption>{m.stem.replace("mascot-","")}</figcaption></figure>' for m in MASCOTS)

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Blocks — every animation, live</title>
<style>
:root{{--coral:#D97757;--coral-deep:#BD5D3A;--red:#E03A2F;--cream:#F0EDE4;--cream-card:#EAE6DA;
 --ink:#191817;--ink-soft:#6B6660;--on:#F7F3EF;
 --shadow:0 20px 60px rgba(0,0,0,.10),0 4px 14px rgba(0,0,0,.05)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);
 font:16px/1.55 -apple-system,BlinkMacSystemFont,"Inter",sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1280px;margin:0 auto;padding:0 26px 110px}}
header{{padding:56px 0 26px;border-bottom:3px solid var(--ink)}}
.eyebrow{{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--coral-deep);font-weight:700}}
h1{{font-size:clamp(34px,5vw,58px);line-height:1.03;margin:12px 0 14px;letter-spacing:-.03em;font-weight:800}}
.lede{{font-size:18px;max-width:76ch;color:var(--ink-soft)}} .lede strong{{color:var(--ink)}}
code{{font-family:ui-monospace,Menlo,monospace;font-size:.86em;background:var(--cream-card);padding:1px 6px;border-radius:5px}}
.blk{{margin-top:42px;background:#fff;border-radius:22px;padding:24px 26px;box-shadow:var(--shadow)}}
.bh{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}}
.bh h2{{margin:0;font:700 27px ui-monospace,Menlo,monospace;letter-spacing:-.02em}}
.cnt{{font-size:13px;color:var(--ink-soft)}}
.badge{{font:800 10px -apple-system,sans-serif;letter-spacing:.12em;padding:4px 9px;border-radius:999px;
 background:var(--coral);color:#fff}}
.b-retired{{background:var(--red)}}
.why{{margin:10px 0 18px;font-size:14.5px;color:var(--ink-soft);max-width:80ch}}
.vs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}}
.v{{margin:0;background:var(--cream);border-radius:14px;overflow:hidden}}
.fh{{position:relative;width:100%;overflow:hidden;background:var(--cream)}}
.fh iframe{{position:absolute;left:0;top:0;border:0;transform-origin:0 0;pointer-events:none;
 transform:scale(var(--s,.19))}}
.v figcaption{{padding:10px 12px 12px;background:#fff;font-size:12px;line-height:1.4;color:var(--ink-soft)}}
.v figcaption a{{display:block;margin-top:5px;font-size:11px;color:var(--coral-deep);text-decoration:none}}
.ms{{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:12px}}
.m{{margin:0;background:var(--cream);border-radius:14px;padding:10px;text-align:center}}
.m img{{width:100%;height:78px;object-fit:contain;image-rendering:pixelated;display:block}}
.m figcaption{{font-size:10px;color:var(--ink-soft);margin-top:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">Library · every animation</div>
  <h1>The blocks, live.</h1>
  <p class="lede">Everything animated in the library, old and new, <strong>running</strong> —
  not screenshots of it. A still of an animated block is the most common complaint, and a stale
  still also freezes whatever the plate looked like the day it was shot, which is how the retired
  graph-paper grid stayed on screen for weeks after it was killed. These iframes always show the
  block as it is <em>now</em>. Every block takes <code>?seek=&lt;s&gt;</code> and is rendered to
  mp4 with <code>scripts/block-render.py</code> before it goes in a cut.</p>
</header>
{"".join(cards)}
<section class="blk">
  <div class="bh"><h2>mascot (platshållare)</h2><span class="cnt">{len(MASCOTS)} animations · outline cut</span></div>
  <p class="why">The mascot is only ever the ACTOR — the thing tending, carrying, conducting or
  reacting. It is never the session, the model, the app or the file. Use the outline cut: a cream
  sticker border that survives any plate.</p>
  <div class="ms">{masc}</div>
</section>
</div>
<script>
function fit(){{document.querySelectorAll(".fh").forEach(function(h){{
  var f=h.querySelector("iframe"); if(!f) return;
  f.style.setProperty("--s",(h.clientWidth/(parseFloat(f.style.width)||1080)).toFixed(4));}});}}
addEventListener("resize",fit); addEventListener("load",fit); fit();
setTimeout(fit,400); setTimeout(fit,1500);
</script>
</body></html>"""

(ROOT / "BLOCKS.html").write_text(page)
n = sum(len(v) for _, _, v, _ in BLOCKS)
print(f"wrote BLOCKS.html — {len(cards)} blocks, {n} variants, {len(MASCOTS)} mascots")
