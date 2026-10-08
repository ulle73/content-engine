"""Writes the three root compositions from ONE template so the formats never drift apart:
  index.html (9:16 1080x1920) · index-4x5.html (1080x1350) · index-1x1.html (1080x1080)
Each mounts the same scene files; data-fmt on the root switches the layout (CSS + JS constants).
Copy this template folder to work/<name>/film first: the 4:5 and 1:1 projects are written as SIBLING folders.
    python build_index.py
"""
from pathlib import Path

DUR = 25.0
SCENES = [  # id, start, duration  (scenes overlap by their transition tails)
    ("s1-hook", 0.0, 3.0),
    ("s2-turn", 3.0, 4.0),
    ("s3-product", 7.0, 6.0),
    ("s4-portals", 13.0, 3.0),
    ("s5-proof", 16.0, 5.0),
    ("s6-cta", 21.0, 4.0),
]
# The master project is this folder (9:16). HyperFrames allows ONE root index.html per project, so the other
# formats are sibling projects (../film-4x5, ../film-1x1) whose compositions/ and assets/ are directory
# junctions back to this folder: one source of truth, three renderable roots.
HERE = Path(__file__).resolve().parent
FORMATS = {HERE: ("9x16", 1080, 1920), HERE.parent / (HERE.name + "-4x5"): ("4x5", 1080, 1350),
           HERE.parent / (HERE.name + "-1x1"): ("1x1", 1080, 1080)}

GRAIN = ("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
         "%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E"
         "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")

HERE = Path(__file__).resolve().parent
# registry component `motion-blur` (npx hyperframes add motion-blur): shutter blur for the elements marked data-hf-motion-blur
_mb = (HERE / "compositions" / "components" / "motion-blur.html").read_text(encoding="utf-8")
MOTION_BLUR_JS = _mb[_mb.index("<script>") + len("<script>"):_mb.index("</script>")]
MOTION_BLUR = '<script src="motion-blur.js"></script>'

TPL = """<!DOCTYPE html>
<html lang="sv">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width={W}, height={H}">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    {MB}
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #01170F; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: #01170F; }}
      .scene {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
      /* film finish: vignette + animated grain (seek-safe jitter below) */
      #fx-vignette {{ position: absolute; inset: 0; pointer-events: none; z-index: 90;
        background: radial-gradient(ellipse 75% 70% at 50% 48%, transparent 55%, rgba(0, 10, 6, 0.55) 100%); }}
      #fx-grain {{ position: absolute; inset: 0; overflow: hidden; pointer-events: none; z-index: 100; }}
      #fx-grain-tex {{ position: absolute; left: -25%; top: -25%; width: 150%; height: 150%;
        background: url("{GRAIN}"); background-size: 300px 300px; opacity: 0.11; mix-blend-mode: overlay; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-fmt="{FMT}" data-start="0" data-duration="{DUR}" data-width="{W}" data-height="{H}" data-fps="30">
{SCENES}
      <audio id="music" data-timeline-role="music" src="assets/soundtrack.wav" data-start="0" data-duration="{DUR}" data-track-index="20" data-volume="1"></audio>
      <div id="fx-vignette"></div>
      <div id="fx-grain"><div id="fx-grain-tex"></div></div>
    </div>
    <script>
      (function () {{
        const tl = gsap.timeline({{ paused: true }});
        // deterministic film-grain jitter, 24 positions per second (hash of the index, no Math.random)
        const step = 1 / 24;
        for (let i = 0; i * step < {DUR}; i++) {{
          const x = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
          const y = Math.abs(Math.sin(i * 78.233) * 12543.1234) % 1;
          tl.set("#fx-grain-tex", {{ x: (x - 0.5) * 240, y: (y - 0.5) * 240 }}, i * step);
        }}
        tl.to({{}}, {{ duration: {DUR} }}, 0);
        window.__timelines["main"] = tl;
      }})();
    </script>
  </body>
</html>
"""

import os, shutil, subprocess
for proj, (fmt, w, h) in FORMATS.items():
    rows = []
    for k, (sid, st, du) in enumerate(SCENES):
        du = min(du, DUR - st)
        rows.append(f'      <div id="el-{sid}" class="scene" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
                    f'data-start="{st}" data-duration="{du:.2f}" data-track-index="{k}" data-width="{w}" data-height="{h}"></div>')
    proj.mkdir(exist_ok=True)
    if proj != HERE:
        # compositions are COPIED with the root height rewritten (a sub-composition's data-height sizes its root);
        # assets are a junction back to the master
        cdir = proj / "compositions"
        if cdir.is_symlink() or (cdir.exists() and os.name == "nt" and os.path.realpath(cdir) != str(cdir)):
            subprocess.run(["cmd", "/c", "rmdir", str(cdir)], check=True, capture_output=True)
        cdir.mkdir(exist_ok=True)
        for f in (HERE / "compositions").glob("*.html"):
            (cdir / f.name).write_text(f.read_text(encoding="utf-8").replace('data-width="1080" data-height="1920"', f'data-width="{w}" data-height="{h}"'), encoding="utf-8")
        for sub in ("assets",):
            link = proj / sub
            if not link.exists():
                if os.name == "nt":
                    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(HERE / sub)], check=True, capture_output=True)
                else:
                    os.symlink(HERE / sub, link)
        for f in ("hyperframes.json", "package.json", "meta.json"):
            shutil.copy(HERE / f, proj / f)
    (proj / "motion-blur.js").write_text(MOTION_BLUR_JS, encoding="utf-8")
    (proj / "index.html").write_text(
        TPL.format(MB=MOTION_BLUR, W=w, H=h, FMT=fmt, DUR=DUR, GRAIN=GRAIN, SCENES="\n".join(rows)), encoding="utf-8")
    print("wrote", proj / "index.html")
