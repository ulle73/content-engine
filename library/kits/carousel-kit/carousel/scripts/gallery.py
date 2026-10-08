"""Build and open carousel/STYLES.html — a visual picker for the style library.

Shows every style sheet from styles.json (sheet + a real example set + what it is best for)
and the own-photo layouts, numbered, so the user can answer "which style?" with a number.
Images are referenced relatively, so the page works offline from the kit folder.

Usage: library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/gallery.py [--no-open]
"""
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent       # carousel/


def build() -> Path:
    cat = json.loads((ROOT / "styles.json").read_text(encoding="utf-8"))
    e = html.escape
    cards = []
    for n, s in enumerate(cat["styles"], 1):
        cards.append(f"""
  <article class="style">
    <header><span class="n">{n}</span><h2>{e(s['name'])}</h2><code>{e(s['id'])}</code></header>
    <img class="sheet" src="{e(s['sheet'])}" alt="{e(s['name'])} style sheet" loading="lazy">
    <img class="ex" src="{e(s['example'])}" alt="example carousel" loading="lazy">
    <p>{e(s['look'])}</p>
    <p class="meta"><b>Best for:</b> {e(', '.join(s['best_for']))}<br>
       <b>Free ($0) images:</b> {e(s['free_images'])}<br>
       <b>Paid:</b> AI images painted from this sheet (+ your logo)</p>
  </article>""")
    lays = []
    for s in cat["own_layouts"]:
        prev = ROOT / s["preview"]
        img = (f'<img src="{e(s["preview"])}" alt="{e(s["name"])}" loading="lazy">' if prev.exists()
               else '<div class="ph">preview</div>')
        lays.append(f'<figure>{img}<figcaption><b>{e(s["name"])}</b><br>{e(s["photo"])}</figcaption></figure>')
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Carousel Styles</title>
<style>
 :root{{--bg:#f6f4ef;--fg:#1c1b19;--mut:#6b675f;--card:#fff;--line:#e3dfd6}}
 @media (prefers-color-scheme:dark){{:root{{--bg:#141412;--fg:#f1efe9;--mut:#a39f96;--card:#1e1d1a;--line:#2f2d29}}}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,system-ui,sans-serif}}
 main{{max-width:1180px;margin:0 auto;padding:40px 16px 80px}}
 h1{{font-size:34px;margin:0 0 4px}} .lede{{color:var(--mut);margin:0 0 32px}}
 .style{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:0 0 24px}}
 .style header{{display:flex;align-items:center;gap:12px;margin-bottom:12px}}
 .style h2{{font-size:22px;margin:0;flex:1}} code{{color:var(--mut)}}
 .n{{width:36px;height:36px;border-radius:50%;background:var(--fg);color:var(--bg);display:grid;place-items:center;font-weight:700}}
 img{{display:block;width:100%;height:auto;border-radius:8px}} .ex{{margin-top:10px}}
 .meta{{color:var(--mut);font-size:14px}}
 h3{{margin:40px 0 6px;font-size:24px}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}}
 figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}}
 figcaption{{font-size:13px;color:var(--mut);margin-top:8px}} .ph{{aspect-ratio:4/5;background:var(--line);border-radius:8px}}
</style></head><body><main>
<h1>Pick a style</h1>
<p class="lede">Tell Claude the number. Every style works free ($0, built on your computer) or paid (AI images).</p>
{''.join(cards)}
<h3>Using your own photos?</h3>
<p class="lede">Claude matches each photo to one of these layouts automatically.</p>
<div class="grid">{''.join(lays)}</div>
</main></body></html>"""
    out = ROOT / "STYLES.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    out = build()
    print(out)
    if "--no-open" not in sys.argv:
        if sys.platform == "win32":
            import os
            os.startfile(str(out))          # Windows: open in the default browser
        elif sys.platform == "darwin":
            subprocess.run(["open", str(out)])
