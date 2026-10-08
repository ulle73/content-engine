"""Layout + contrast check for template-own.html.

Geometry: every text element inside the frame (24px margin) and no two text elements
overlapping (except pairs sharing a data-ov group, e.g. punch caps + script).

Contrast (pixel level): the slide is screenshotted with all text hidden — the FINAL backdrop
(photo + grade + every scrim/pool/grain the template added). For each text element the pixels
behind its box are sampled, and the text colour is compared with the worst case: the 90th
luminance percentile when the text is lighter than the backdrop, the 10th when darker.
Targets: 3:1 for large type (>= 40px, or >= 30px bold), 4.5:1 otherwise.
Text that sits BEHIND the subject cutout is measured against the backdrop without the cutout.

Usage: library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/check_own.py <run_dir> [--save-backdrops]
"""
import io, json, re, sys, time
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    raise SystemExit("usage: library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/check_own.py <run_dir> [--save-backdrops]")
RUN = Path(args[0])
SAVE = "--save-backdrops" in sys.argv
sys.path.insert(0, str(HERE))
import carousel_render as cr
import carousel_charts
from playwright.sync_api import sync_playwright

plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
tpl = (HERE / plan["template"]).read_text(encoding="utf-8")
carousel_charts.use_theme(plan.get("theme"))

COLLECT = """() => { const s=document.getElementById('stage').getBoundingClientRect();
 const els=[...document.querySelectorAll('.tx'), ...document.querySelectorAll('.tx em')]
   .filter(e=>e.offsetParent!==null && e.textContent.trim());
 return els.map(e=>{ const r=e.getBoundingClientRect(), cs=getComputedStyle(e);
  return {t:e.textContent.trim().replace(/\\s+/g,' ').slice(0,28), tag:e.tagName, ov:e.dataset.ov||'',
    behind:e.classList.contains('behind') || !!e.closest('.behind'), color:cs.color, opacity:+cs.opacity,
    size:parseFloat(cs.fontSize), weight:parseInt(cs.fontWeight)||400,
    x:r.left-s.left, y:r.top-s.top, r:r.right-s.left, b:r.bottom-s.top}; }); }"""


def lin(v):
    v = v / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def rl_img(a):
    a = a.astype(np.float64)
    return 0.2126 * lin(a[..., 0]) + 0.7152 * lin(a[..., 1]) + 0.0722 * lin(a[..., 2])


def parse_color(c):
    m = re.findall(r"[\d.]+", c)
    r, g, b = (float(x) for x in m[:3])
    a = float(m[3]) if len(m) > 3 else 1.0
    return np.array([r, g, b]), a


def contrast(a, b):
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def shot(pg):
    return np.array(Image.open(io.BytesIO(pg.locator("#stage").screenshot())).convert("RGB"))


bad = 0
with sync_playwright() as p:
    br = cr.cfg.launch_browser(p)
    pg = br.new_page(viewport={"width": 1080, "height": 1350})
    for sl in plan["slides"]:
        t0 = time.time()
        pg.evaluate("window.__ownReady = false")   # set_content keeps the window: clear the old flag
        pg.set_content(cr._slide_html(tpl, sl, plan), wait_until="networkidle")
        pg.wait_for_function("window.__ownReady === true", timeout=15000)
        dt = time.time() - t0
        els = pg.evaluate(COLLECT)
        warn = pg.evaluate("document.body.dataset.warn || ''")
        probs = []
        # ---- geometry
        for e in els:
            if e["tag"] == "EM":
                continue
            if e["x"] < 24 or e["y"] < 24 or e["r"] > 1056 or e["b"] > 1326:
                probs.append(f"outside frame: '{e['t']}' ({e['x']:.0f},{e['y']:.0f})-({e['r']:.0f},{e['b']:.0f})")
        geo = [e for e in els if e["tag"] != "EM"]
        for i, a in enumerate(geo):
            for c in geo[i + 1:]:
                if a["ov"] and a["ov"] == c["ov"]:
                    continue
                if a["x"] < c["r"] - 2 and c["x"] < a["r"] - 2 and a["y"] < c["b"] - 2 and c["y"] < a["b"] - 2:
                    probs.append(f"overlap: '{a['t']}' x '{c['t']}'")
        # ---- contrast against the final backdrop
        pg.add_style_tag(content=".tx{visibility:hidden !important}")
        front = shot(pg)
        pg.add_style_tag(content="#cut{visibility:hidden !important}")
        behind = shot(pg)
        if SAVE:
            Image.fromarray(front).save(RUN / f"backdrop{sl['index']:02d}.png")
        rl_front, rl_behind = rl_img(front), rl_img(behind)
        lows = []
        for e in els:
            x0, y0 = int(max(0, e["x"])), int(max(0, e["y"]))
            x1, y1 = int(min(1080, e["r"])), int(min(1350, e["b"]))
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            L = (rl_behind if e["behind"] else rl_front)[y0:y1, x0:x1]
            p10, p50, p90 = np.percentile(L, [10, 50, 90])
            rgb, alpha = parse_color(e["color"])
            alpha *= e["opacity"]
            base = (behind if e["behind"] else front)[y0:y1, x0:x1].reshape(-1, 3).mean(0)
            eff = alpha * rgb + (1 - alpha) * base
            tl = float(rl_img(eff[None, None, :])[0, 0])
            worst = p90 if tl > p50 else p10
            c = contrast(tl, worst)
            large = e["size"] >= 40 or (e["size"] >= 30 and e["weight"] >= 700)
            target = 3.0 if large else 4.5
            lows.append(c)
            if c < target:
                probs.append(f"contrast {c:.2f} < {target}: '{e['t']}' ({e['size']:.0f}px)")
        bad += len(probs)
        print(f"slide {sl['index']} [{sl.get('layout')}] {dt*1000:.0f}ms  min contrast {(min(lows) if lows else 0):.2f}  "
              f"{'OK' if not probs else ''}" + (f"  warn: {warn}" if warn else ""))
        for q in probs:
            print("   - " + q)
    br.close()
print("check:", "clean" if not bad else f"{bad} problem(s)")
