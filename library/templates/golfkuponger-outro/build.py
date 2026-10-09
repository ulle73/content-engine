"""Golfkuponger outro (slutbild): the original swinging logo + its sound on brand green, with six finishes.

The logo animation and its sound are the owner's originals, untouched: assets/logo-swing.webm is the source cut out of
its black background (alpha = max channel, colour unpremultiplied, so the gold is identical on green) and
assets/logo-sound.wav is the original audio. Only what happens around it varies per variant.

    python build.py [--out DIR] [--formats 9x16,4x5,1x1] [--variants klassisk,glod,...]

Writes one HyperFrames project per variant/format; render.py renders them and muxes the original sound.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DURATION = 4.0
LOGO_END = 2.52  # length of the original logo animation
GREEN = "#0e1f15"
GOLD = "#d6a536"
CREAM = "#f6f3ec"
LINES = ("Mer golf.", "Fler upplevelser.")

# Logo element: the cut-out is 960x912; the finished logo's bounding box inside it is x 165..940, y 43..892.
FORMATS = {
    "9x16": {"W": 1080, "H": 1920, "logo_w": 912, "logo_cy": 820, "text_y": 1320, "font": 108},
    "4x5": {"W": 1080, "H": 1350, "logo_w": 700, "logo_cy": 515, "text_y": 965, "font": 90},
    "1x1": {"W": 1080, "H": 1080, "logo_w": 580, "logo_cy": 390, "text_y": 750, "font": 78},
}
VARIANTS = ("klassisk", "glod", "stralar", "stoft", "spotlight", "minimal")
LABELS = {
    "klassisk": "Klassisk glans – ljussvep över loggan, raderna glider upp, penseldraget ritas",
    "glod": "Guldglöd – varm glöd blommar bakom loggan, orden tonar in ur oskärpa, gnistor på ringen",
    "stralar": "Ljusstrålar – mjuka strålar roterar bakom loggan, raderna glider upp ur en mask",
    "stoft": "Guldstoft – guldpartiklar sprids när ringen landar, texten dras ihop från bred spärrning",
    "spotlight": "Spotlight – scenen öppnas ur mörker, långsam inzoomning, texten skrivs fram",
    "minimal": "Minimal premium – filmkorn och vinjett, bokstäverna faller på plats, guldskimmer över texten",
}


def layout(fmt: str) -> dict:
    f = dict(FORMATS[fmt])
    scale = f["logo_w"] / 960
    f["logo_h"] = round(912 * scale)
    # centre the finished logo's bounding box (x 165..940 -> 552.5, y 43..892 -> 467.5) horizontally / at logo_cy
    f["logo_left"] = round(f["W"] / 2 - 552.5 * scale)
    f["logo_top"] = round(f["logo_cy"] - 467.5 * scale)
    f["logo_cx"] = f["W"] / 2
    f["line_h"] = round(f["font"] * 1.05)
    return f


def chars(text: str, cls: str) -> str:
    return "".join(f'<span class="{cls}">{"&nbsp;" if c == " " else c}</span>' for c in text)


def words(text: str, cls: str) -> str:
    return " ".join(f'<span class="{cls}">{w}</span>' for w in text.split(" "))


def particles(n: int, cx: float, cy: float, spread: float) -> tuple[str, list[tuple]]:
    """Deterministic gold dust: (dx, dy, size, delay) per particle, no randomness at render time."""
    import math

    out, data = [], []
    for i in range(n):
        a = (i * 137.508) % 360
        r = spread * (0.35 + ((i * 0.618) % 1) * 0.65)
        dx, dy = r * math.cos(math.radians(a)), r * math.sin(math.radians(a)) * 0.8
        size = 3 + (i * 7 % 6)
        out.append(f'<i class="dust" id="d{i}" style="left:{cx - size / 2:.0f}px;top:{cy - size / 2:.0f}px;'
                   f'width:{size}px;height:{size}px"></i>')
        data.append((round(dx), round(dy), round(((i * 0.37) % 1) * 0.25, 3)))
    return "".join(out), data


def html(variant: str, fmt: str) -> str:
    f = layout(fmt)
    W, H = f["W"], f["H"]
    text_split = {"glod": "words", "stoft": "chars", "minimal": "chars"}.get(variant, "lines")

    def line(i: int, text: str) -> str:
        body = {"words": words(text, "w"), "chars": chars(text, "c")}.get(text_split, text)
        if i == 1:
            head, tail = body.split("upplevelser", 1) if text_split == "lines" else (body, "")
            if text_split == "lines":
                body = f'{head}<span class="hl">upplevelser</span>{tail}'
        return f'<div class="ln-mask"><div class="ln" id="ln{i}">{body}</div></div>'

    text_block = "".join(line(i, t) for i, t in enumerate(LINES))
    brush = f"""
      <svg id="brush" viewBox="0 0 600 70" width="{round(f['font'] * 6.2)}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="gold" x1="0" x2="1"><stop offset="0" stop-color="#b8892a"/><stop offset=".45" stop-color="#e2bd6a"/><stop offset="1" stop-color="#c79a3e"/></linearGradient>
          <filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.9 0.08" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="7"/></filter>
        </defs>
        <g filter="url(#rough)" fill="url(#gold)">
          <path d="M6 20 C 140 9, 330 4, 594 10 L 592 26 C 360 24, 170 30, 10 38 Z" opacity=".95"/>
          <path d="M88 50 C 220 42, 360 40, 500 43 L 498 54 C 360 53, 240 58, 92 64 Z" opacity=".9"/>
        </g>
      </svg>"""
    extras = ""
    if variant == "glod":
        extras += f'<div id="glow" style="left:{f["logo_cx"] - 420:.0f}px;top:{f["logo_cy"] - 420}px"></div>'
        for i, (x, y) in enumerate([(0.83, 0.20), (0.90, 0.62), (0.47, 0.96), (0.70, 0.08)]):
            extras += (f'<svg class="spark" id="sp{i}" viewBox="0 0 40 40" style="left:{f["logo_left"] + x * f["logo_w"] - 22:.0f}px;'
                       f'top:{f["logo_top"] + y * f["logo_h"] - 22:.0f}px"><path d="M20 0 L23 17 L40 20 L23 23 L20 40 L17 23 L0 20 L17 17 Z" fill="#fff6dc"/></svg>')
    if variant == "stralar":
        extras += f'<div id="rays" style="left:{f["logo_cx"] - 700:.0f}px;top:{f["logo_cy"] - 700}px"></div>'
    dust_data = []
    if variant == "stoft":
        dust_html, dust_data = particles(46, f["logo_cx"], f["logo_cy"] + 40, f["logo_w"] * 0.62)
        extras += f'<div id="dustbox">{dust_html}</div>'
    if variant == "spotlight":
        extras += '<div id="spot"></div>'
    finish = '<div id="vig"></div><div id="grain"><div id="grain-tex"></div></div>' if variant in {"minimal", "spotlight", "glod", "stralar", "stoft"} else ""
    bg = GREEN if variant == "klassisk" else f"radial-gradient(ellipse 70% 55% at 50% {f['logo_cy'] / H * 100:.0f}%, #16301f 0%, {GREEN} 55%, #0a1610 100%)"
    shine = variant in {"klassisk", "stralar", "spotlight", "minimal", "stoft"}
    logo_box = (f'left:{f["logo_left"]}px;top:{f["logo_top"]}px;width:{f["logo_w"]}px;height:{f["logo_h"]}px')

    js_variant = {
        "klassisk": """
        tl.from("#ln0", {y: 60, opacity: 0, duration: .55, ease: "power3.out"}, 2.35)
          .from("#ln1", {y: 60, opacity: 0, duration: .55, ease: "power3.out"}, 2.55);
        brushIn(2.95); shineAt(2.6);""",
        "glod": """
        tl.fromTo("#glow", {opacity: 0, scale: .7}, {opacity: .75, scale: 1.05, duration: .9, ease: "power2.out"}, 2.25)
          .to("#glow", {opacity: .55, scale: 1, duration: .85, ease: "sine.inOut"}, 3.15);
        tl.from(".w", {opacity: 0, filter: "blur(14px)", y: 18, duration: .5, stagger: .09, ease: "power2.out"}, 2.4);
        gsap.utils.toArray(".spark").forEach((el, i) => {
          tl.fromTo(el, {scale: 0, opacity: 0, rotate: -40}, {scale: 1, opacity: 1, rotate: 0, duration: .22, ease: "back.out(3)"}, 2.5 + i * .18)
            .to(el, {scale: 0, opacity: 0, rotate: 30, duration: .35, ease: "power2.in"}, 2.78 + i * .18);
        });
        brushIn(3.0);""",
        "stralar": """
        tl.fromTo("#rays", {opacity: 0, rotate: -8}, {opacity: .5, rotate: 0, duration: 1.0, ease: "power2.out"}, 2.1)
          .to("#rays", {rotate: 9, duration: 1.9, ease: "none"}, 2.1);
        tl.from("#ln0", {yPercent: 105, duration: .6, ease: "expo.out"}, 2.4)
          .from("#ln1", {yPercent: 105, duration: .6, ease: "expo.out"}, 2.58);
        brushIn(3.0); shineAt(2.55);""",
        "stoft": """
        DUST.forEach(([dx, dy, d], i) => {
          tl.fromTo("#d" + i, {x: 0, y: 0, opacity: 0, scale: .4},
            {x: dx, y: dy, opacity: 1, scale: 1, duration: .55, ease: "expo.out"}, 2.42 + d)
            .to("#d" + i, {y: dy - 60, opacity: 0, duration: 1.0, ease: "sine.in"}, 2.97 + d);
        });
        tl.from(".ln", {letterSpacing: "0.45em", opacity: 0, filter: "blur(10px)", duration: .8, stagger: .15, ease: "power3.out"}, 2.45);
        brushIn(3.1); shineAt(2.7);""",
        "spotlight": """
        tl.fromTo("#spot", {"--r": "0%"}, {"--r": "140%", duration: 1.3, ease: "power2.inOut"}, 0)
          .fromTo("#stage", {scale: 1}, {scale: 1.04, duration: 4.0, ease: "none", transformOrigin: "50% 45%"}, 0);
        tl.fromTo("#ln0", {clipPath: "inset(0 100% 0 0)"}, {clipPath: "inset(0 0% 0 0)", duration: .45, ease: "power1.inOut"}, 2.35)
          .fromTo("#ln1", {clipPath: "inset(0 100% 0 0)"}, {clipPath: "inset(0 0% 0 0)", duration: .6, ease: "power1.inOut"}, 2.75);
        brushIn(3.25); shineAt(2.6);""",
        "minimal": """
        tl.fromTo("#logo-wrap", {y: 0}, {y: -10, duration: 4.0, ease: "sine.inOut"}, 0);
        tl.from(".c", {y: 46, opacity: 0, rotate: 6, duration: .5, stagger: .022, ease: "back.out(2)"}, 2.35);
        tl.fromTo("#text", {"--sh": "-30%"}, {"--sh": "130%", duration: .8, ease: "power1.inOut"}, 3.15);
        brushIn(3.0); shineAt(2.55);""",
    }[variant]

    return f"""<!DOCTYPE html>
<html lang="sv">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width={W}, height={H}">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Caveat Brush"; src: url("assets/fonts/CaveatBrush-Regular.ttf") format("truetype"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {GREEN}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: {bg}; }}
      #stage {{ position: absolute; inset: 0; }}
      #logo-wrap {{ position: absolute; {logo_box}; }}
      #logo-wrap video, #logo-wrap img {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
      #logo-final {{ opacity: 0; }}
      #logo-shine {{ opacity: 0; filter: brightness(3.1) saturate(1.1);
        -webkit-mask-image: linear-gradient(105deg, transparent calc(var(--s) - 7%), #000 var(--s), transparent calc(var(--s) + 7%));
        mask-image: linear-gradient(105deg, transparent calc(var(--s) - 7%), #000 var(--s), transparent calc(var(--s) + 7%)); --s: -20%; }}
      #glint {{ position: absolute; width: 90px; height: 90px; opacity: 0; filter: drop-shadow(0 0 16px rgba(255,236,180,1)); }}
      #text {{ position: absolute; left: 0; right: 0; top: {f['text_y']}px; text-align: center; font-family: "Caveat Brush", cursive;
        font-size: {f['font']}px; line-height: {f['line_h']}px; color: {CREAM}; text-shadow: 0 2px 18px rgba(0,0,0,.35); --sh: -30%; }}
      .ln-mask {{ overflow: hidden; padding: 0 20px 8px; }}
      .ln {{ display: inline-block; white-space: nowrap; }}
      .w, .c {{ display: inline-block; }}
      #text.shimmer .ln, #text .ln {{ }}
      #shimmer {{ position: absolute; inset: 0; pointer-events: none; mix-blend-mode: overlay;
        background: linear-gradient(100deg, transparent calc(var(--sh) - 12%), rgba(255,226,150,.95) var(--sh), transparent calc(var(--sh) + 12%)); }}
      #brush-wrap {{ display: flex; justify-content: center; margin-top: {round(f['font'] * -0.05)}px; clip-path: inset(0 100% 0 0); }}
      #brush {{ height: {round(f['font'] * 0.62)}px; }}
      #glow {{ position: absolute; width: 840px; height: 840px; border-radius: 50%; opacity: 0;
        background: radial-gradient(circle, rgba(232,190,96,.55) 0%, rgba(214,165,54,.22) 38%, rgba(214,165,54,0) 70%); filter: blur(30px); }}
      .spark {{ position: absolute; width: 44px; height: 44px; opacity: 0; filter: drop-shadow(0 0 10px rgba(255,230,160,.95)); }}
      #rays {{ position: absolute; width: 1400px; height: 1400px; opacity: 0; border-radius: 50%;
        background: repeating-conic-gradient(from 0deg, rgba(240,205,120,.16) 0deg 5deg, rgba(240,205,120,0) 5deg 18deg);
        -webkit-mask-image: radial-gradient(circle, #000 12%, transparent 62%); mask-image: radial-gradient(circle, #000 12%, transparent 62%); }}
      #dustbox {{ position: absolute; inset: 0; pointer-events: none; }}
      .dust {{ position: absolute; border-radius: 50%; opacity: 0; background: radial-gradient(circle, #fff3c8 0%, {GOLD} 55%, rgba(214,165,54,0) 100%);
        box-shadow: 0 0 8px rgba(240,200,110,.9); }}
      #spot {{ position: absolute; inset: 0; pointer-events: none; z-index: 50; --r: 0%;
        background: radial-gradient(circle at 50% {f['logo_cy'] / H * 100:.0f}%, transparent calc(var(--r) * .55), rgba(5,12,8,.97) var(--r)); }}
      #vig {{ position: absolute; inset: 0; pointer-events: none; z-index: 60;
        background: radial-gradient(ellipse 78% 70% at 50% 48%, transparent 55%, rgba(0,8,4,.55) 100%); }}
      #grain {{ position: absolute; inset: 0; overflow: hidden; pointer-events: none; z-index: 70; }}
      #grain-tex {{ position: absolute; left: -25%; top: -25%; width: 150%; height: 150%; opacity: .09; mix-blend-mode: overlay;
        background: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); background-size: 300px 300px; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DURATION}" data-width="{W}" data-height="{H}" data-fps="30">
      <div id="stage">
        {extras}
        <div id="logo-wrap">
          <video id="logo-video" src="assets/logo-swing.webm" muted playsinline data-start="0" data-duration="{LOGO_END}" data-track-index="1"></video>
          <img id="logo-final" src="assets/logo-final.png" alt="">
          {'<img id="logo-shine" src="assets/logo-final.png" alt="">' if shine else ''}
        </div>
        {f'<svg id="glint" viewBox="0 0 40 40" style="left:{f["logo_left"] + 0.80 * f["logo_w"] - 45:.0f}px;top:{f["logo_top"] + 0.13 * f["logo_h"] - 45:.0f}px"><path d="M20 0 L22.5 17.5 L40 20 L22.5 22.5 L20 40 L17.5 22.5 L0 20 L17.5 17.5 Z" fill="#fff8e6"/></svg>' if shine else ''}
        <div id="text">{text_block}<div id="brush-wrap">{brush}</div>{'<div id="shimmer"></div>' if variant == "minimal" else ''}</div>
      </div>
      {finish}
    </div>
    <script>
      (function () {{
        const tl = gsap.timeline({{ paused: true }});
        const DUST = {json.dumps([list(t) for t in dust_data])};
        function brushIn(at) {{ tl.to("#brush-wrap", {{ clipPath: "inset(0 0% 0 0)", duration: .45, ease: "power2.out" }}, at); }}
        function shineAt(at) {{
          tl.set("#logo-shine", {{ opacity: 1 }}, at)
            .fromTo("#logo-shine", {{ "--s": "-20%" }}, {{ "--s": "120%", duration: .75, ease: "power1.inOut" }}, at)
            .set("#logo-shine", {{ opacity: 0 }}, at + .76)
            .fromTo("#glint", {{ scale: 0, opacity: 0, rotate: -45 }}, {{ scale: 1, opacity: 1, rotate: 0, duration: .2, ease: "back.out(3)" }}, at + .5)
            .to("#glint", {{ scale: 0, opacity: 0, rotate: 45, duration: .3, ease: "power2.in" }}, at + .72);
        }}
        tl.set("#logo-final", {{ opacity: 1 }}, {LOGO_END - 0.04});
        {js_variant}
        if (document.getElementById("grain-tex")) {{
          const step = 1 / 24;
          for (let i = 0; i * step < {DURATION}; i++) {{
            const x = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1, y = Math.abs(Math.sin(i * 78.233) * 12543.1234) % 1;
            tl.set("#grain-tex", {{ x: (x - .5) * 240, y: (y - .5) * 240 }}, i * step);
          }}
        }}
        tl.to({{}}, {{ duration: {DURATION} }}, 0);
        window.__timelines["main"] = tl;
      }})();
    </script>
  </body>
</html>
"""


def build(out: Path, formats: list[str], variants: list[str]) -> list[Path]:
    projects = []
    for variant in variants:
        for fmt in formats:
            project = out / f"{variant}-{fmt}"
            if project.exists():
                shutil.rmtree(project)
            shutil.copytree(HERE / "assets", project / "assets")
            (project / "index.html").write_text(html(variant, fmt), encoding="utf-8")
            (project / "hyperframes.json").write_text('{"paths": {"assets": "assets"}, "media": {"autoProxy": true}}', encoding="utf-8")
            projects.append(project)
    return projects


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE.parents[2] / "work" / "gk-outro"))
    parser.add_argument("--formats", default="9x16")
    parser.add_argument("--variants", default=",".join(VARIANTS))
    a = parser.parse_args()
    for p in build(Path(a.out), a.formats.split(","), a.variants.split(",")):
        print(p)
