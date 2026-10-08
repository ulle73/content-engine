#!/usr/bin/env python3
"""
Render library/concepts.json as a browsable page with LIVE previews — every block runs in an
iframe, so you judge the animation, not a still.

    python scripts/build-concept-catalog.py     # -> CONCEPTS.html at the repo root

Serve the repo root and open http://127.0.0.1:8080/CONCEPTS.html
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "library/concepts.json").read_text())

KIND_LABEL = {"block": "LIVE BLOCK", "image": "IMAGE", "mascot": "MASCOT",
              "note": "IN-COMP", "gap": "MISSING"}

def asset_card(a):
    kind, src, label = a["kind"], a["src"], a["label"]
    if kind == "block":
        # A block declares the slot it is built for. Preview it at THAT aspect — a 1000x880
        # split rendered inside a 9:16 card looks identical to the full-frame version, which
        # is exactly the confusion this catalog exists to remove.
        fit = "full"
        if "fit=half" in src: fit = "half"
        elif "fit=head" in src: fit = "head"
        W, H = {"full": (1080, 1920), "half": (1000, 880), "head": (1000, 620)}[fit]
        body = (f'<div class="frameholder f-{fit}" style="aspect-ratio:{W}/{H}">'
                f'<iframe src="{src}" loading="lazy" scrolling="no" tabindex="-1" '
                f'style="width:{W}px;height:{H}px;--fw:{W}"></iframe>'
                f'<span class="fitbadge">{fit.upper()} · {W}×{H}</span></div>')
    elif kind in ("image", "mascot"):
        body = f'<div class="imgholder"><img src="{src}" loading="lazy" alt=""></div>'
    elif kind == "gap":
        body = '<div class="gapholder">nothing in the library covers this yet</div>'
    else:
        body = '<div class="noteholder">built in the composition, not a library file</div>'
    link = (f'<a class="open" href="{src}" target="_blank">open ↗</a>'
            if src else "")
    return f"""<figure class="asset k-{kind}">
      {body}
      <figcaption><span class="kind">{KIND_LABEL.get(kind, kind.upper())}</span>
        <b>{html.escape(label)}</b>{link}</figcaption>
    </figure>"""

sections = []
for c in DATA["concepts"]:
    says = "".join(f'<span class="say">{html.escape(s)}</span>' for s in c["say"])
    assets = "".join(asset_card(a) for a in c["assets"])
    gap = " has-gap" if any(a["kind"] == "gap" for a in c["assets"]) else ""
    sections.append(f"""
<section class="concept{gap}" id="c-{c['id']}">
  <div class="head">
    <h2>{html.escape(c['id'])}</h2>
    <span class="count">{c['count']} mentions across the scripts</span>
  </div>
  <div class="says">{says}</div>
  <div class="rulepair">
    <p class="do"><b>Show</b> {html.escape(c['show'])}</p>
    <p class="dont"><b>Never</b> {html.escape(c['never'])}</p>
  </div>
  <div class="assets">{assets}</div>
</section>""")

rules = "".join(f"<li>{html.escape(r)}</li>" for r in DATA["rules"])
nav = "".join(f'<a href="#c-{c["id"]}">{html.escape(c["id"])}</a>' for c in DATA["concepts"])

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Concept catalog — what to show for what he says</title>
<style>
:root{{--coral:#D97757;--coral-deep:#BD5D3A;--red:#E03A2F;--cream:#F0EDE4;--cream-card:#EAE6DA;
  --ink:#191817;--ink-soft:#6B6660;--dark:#201512;--on:#F7F3EF;--ok:#3F7A43;
  --shadow:0 20px 60px rgba(0,0,0,.10),0 4px 14px rgba(0,0,0,.05)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Inter",sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1280px;margin:0 auto;padding:0 26px 110px}}
header{{padding:56px 0 26px;border-bottom:3px solid var(--ink)}}
.eyebrow{{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--coral-deep);font-weight:700}}
h1{{font-size:clamp(34px,5vw,58px);line-height:1.03;margin:12px 0 14px;letter-spacing:-.03em;font-weight:800}}
.lede{{font-size:18px;max-width:76ch;color:var(--ink-soft)}} .lede strong{{color:var(--ink)}}
code{{font-family:ui-monospace,Menlo,monospace;font-size:.86em;background:var(--cream-card);
  padding:1px 6px;border-radius:5px}}
.rules{{margin:22px 0 0;padding:20px 24px;background:var(--ink);color:#D9D2C8;border-radius:16px}}
.rules ol{{margin:0;padding-left:20px;font-size:14.5px;line-height:1.6}}
.rules li{{margin-bottom:6px}} .rules li:first-child{{color:#fff;font-weight:600}}
nav{{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 0}}
nav a{{font:700 12px/1 -apple-system,sans-serif;letter-spacing:.06em;text-transform:uppercase;
  text-decoration:none;color:var(--ink);background:#fff;padding:9px 13px;border-radius:999px;
  box-shadow:var(--shadow)}}
nav a:hover{{background:var(--coral);color:#fff}}

.concept{{margin-top:44px;background:#fff;border-radius:22px;padding:26px 28px;box-shadow:var(--shadow)}}
.concept.has-gap{{border-left:6px solid var(--red)}}
.head{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}}
.head h2{{margin:0;font-size:30px;letter-spacing:-.02em;font-family:ui-monospace,Menlo,monospace}}
.count{{font-size:13px;color:var(--ink-soft)}}
.says{{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 16px}}
.say{{font:600 13px ui-monospace,Menlo,monospace;background:var(--cream);color:var(--ink-soft);
  padding:5px 11px;border-radius:8px}}
.rulepair{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px}}
@media(max-width:760px){{.rulepair{{grid-template-columns:1fr}}}}
.do,.dont{{margin:0;font-size:14.5px;line-height:1.5;padding:14px 16px;border-radius:12px}}
.do{{background:#EFF6EF;color:#2C4A2E}} .do b{{color:var(--ok);display:block;font-size:11px;
  letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}}
.dont{{background:#FDF1ED;color:#6B3A2C}} .dont b{{color:var(--red);display:block;font-size:11px;
  letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}}

.assets{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}}
.asset{{margin:0;background:var(--cream);border-radius:16px;overflow:hidden}}
.frameholder{{position:relative;width:100%;overflow:hidden;background:var(--cream)}}
.frameholder iframe{{position:absolute;left:0;top:0;border:0;transform-origin:0 0;
  pointer-events:none;transform:scale(var(--s,.2))}}
.fitbadge{{position:absolute;left:8px;bottom:8px;z-index:2;font:800 9px -apple-system,sans-serif;
  letter-spacing:.1em;background:rgba(25,24,23,.8);color:#fff;padding:4px 7px;border-radius:6px}}
.imgholder{{aspect-ratio:9/16;display:flex;align-items:center;justify-content:center;padding:18px;
  background:var(--cream-card)}}
.imgholder img{{max-width:100%;max-height:100%;object-fit:contain;image-rendering:pixelated}}
.gapholder,.noteholder{{aspect-ratio:9/16;display:flex;align-items:center;justify-content:center;
  text-align:center;padding:20px;font-size:13px;color:var(--ink-soft);background:var(--cream-card)}}
.gapholder{{background:#FDF1ED;color:#A33B25;font-weight:600}}
figcaption{{padding:12px 14px 14px;background:#fff}}
.kind{{display:inline-block;font:800 9.5px -apple-system,sans-serif;letter-spacing:.12em;
  background:var(--ink);color:var(--on);padding:4px 8px;border-radius:999px;margin-bottom:7px}}
.k-gap .kind{{background:var(--red)}} .k-block .kind{{background:var(--coral)}}
figcaption b{{display:block;font-size:12.5px;line-height:1.4;font-weight:600}}
.open{{display:inline-block;margin-top:8px;font-size:11.5px;color:var(--coral-deep);text-decoration:none}}
.open:hover{{text-decoration:underline}}
</style></head><body><div class="wrap">

<header>
  <div class="eyebrow">Library · knowledge base</div>
  <h1>What to show, for what he says.</h1>
  <p class="lede">The editor's lookup. Read it <strong>before</strong> choosing any asset:
  find what the line is about, use what's under it. Terms and counts are mined from the 22
  shipped transcripts, so the list is what he actually talks about — not what the library happens
  to contain. Every block below is <strong>live and animating</strong>, not a screenshot.</p>
  <div class="rules"><ol>{rules}</ol></div>
  <nav>{nav}</nav>
</header>

{"".join(sections)}

</div>
<script>
/* Scale every preview from its MEASURED width. This used to be a CSS calc() on container-query
   units, which silently resolves to transform:none — so all 19 previews rendered at full
   1080x1920 inside a 220px card and only their blank top-left corner was visible. */
function fitPreviews(){{
  document.querySelectorAll(".frameholder").forEach(function(h){{
    var f = h.querySelector("iframe"); if (!f) return;
    var native = parseFloat(f.style.width) || 1080;
    f.style.setProperty("--s", (h.clientWidth / native).toFixed(4));
  }});
}}
addEventListener("resize", fitPreviews);
addEventListener("load", fitPreviews);
fitPreviews();
setTimeout(fitPreviews, 400); setTimeout(fitPreviews, 1500);
</script>
</body></html>"""

(ROOT / "CONCEPTS.html").write_text(page)
n_assets = sum(len(c["assets"]) for c in DATA["concepts"])
gaps = [c["id"] for c in DATA["concepts"] if any(a["kind"] == "gap" for a in c["assets"])]
print(f"wrote CONCEPTS.html — {len(DATA['concepts'])} concepts, {n_assets} assets, gaps: {gaps or 'none'}")
