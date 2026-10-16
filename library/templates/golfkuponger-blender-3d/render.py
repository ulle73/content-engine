"""Renderar en Blender-effekt och gör färdiga klipp med alfa + kontroller. Bara standardbiblioteket.

  python library/templates/golfkuponger-blender-3d/render.py titel --out work/<projekt>/3d/titel --set text="MER GOLF"
  python library/templates/golfkuponger-blender-3d/render.py golfboll --out work/<projekt>/3d/boll --test
  python library/templates/golfkuponger-blender-3d/render.py presets/titel.json --out ...    (JSON med nycklar)

--test = 50 % upplösning och 16 samples (titta på det först), annars 100 % och 64 samples.
--set nyckel=värde (flera går bra; värdet tolkas som JSON om det går, t.ex. --set frames=90 --set x=497).
--bara-bilder N,N,... renderar bara de bildrutorna (snabb stillbildskontroll).

Utdata i --out:
  frames/f_0001.png …   PNG-sekvens RGBA (källan)
  <namn>.mov            ProRes 4444 med alfa (yuva444p10le) – för FilmCraft/Resolve/Premiere
  <namn>.webm           VP9 med alfa (yuva420p) – för Remotion (<OffthreadVideo transparent>) och HyperFrames
  <namn>-forhand.mp4    H.264 över mörkgrönt #082f27 – förhandsvisning, ingen alfa
  kontroll-magenta.png  4 bildrutor på magenta (kanter/halo syns direkt) + röda safe zone-linjer
  qa.json               motivets ruta per bildruta mot safe zones, läsregel (titel)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
BG = "0x082f27"


def run(cmd: list[str]) -> None:
    print("›", " ".join(str(c) for c in cmd[:6]), "…")
    subprocess.run(cmd, check=True)


def ff(*args: str) -> None:
    run(["ffmpeg", "-v", "error", "-y", *args])


def safe_zones(qa: dict, frames: Path, scale: float) -> None:
    """Motivets verkliga ruta per bildruta ur alfan (ffmpeg bbox, alfa ≥ 160 – den mjuka skuggan räknas som dekor),
    i 1080x1920-koordinater. Kontrolleras från landningen till ev. utgång; inrörelsen får passera kanten."""
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", str(frames / "f_%04d.png"), "-vf",
                        "alphaextract,bbox=min_val=160", "-f", "null", "-"], capture_output=True, text=True)
    x0, y0, x1, y1 = qa["safe_zone"]
    rows, ok = [], True
    for line in p.stderr.splitlines():
        if "Parsed_bbox" not in line or " n:" not in line:
            continue
        kv = dict(t.split(":", 1) for t in line.split("] ", 1)[1].split() if ":" in t)
        f = int(kv["n"]) + 1
        box = [round(int(kv[k]) / scale) for k in ("x1", "y1", "x2", "y2")] if "x1" in kv else None
        check = f >= qa["settle"] and (qa["exit_start"] is None or f <= qa["exit_start"])
        inside = box is None or (box[0] >= x0 and box[1] >= y0 and box[2] <= x1 and box[3] <= y1)
        ok &= inside or not check
        rows.append({"frame": f, "box": box, "checked": check, "inside": inside})
    qa["safe_ok"] = ok and bool(rows)
    qa["rows"] = rows
    bad = [r for r in rows if r["checked"] and not r["inside"]]
    if bad:
        print(f"Utanför safe zones i {len(bad)} bildrutor, t.ex. bildruta {bad[0]['frame']}: {bad[0]['box']}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("effekt", help="titel | golfboll | sökväg till JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="NYCKEL=VÄRDE")
    ap.add_argument("--test", action="store_true", help="50 %% upplösning, 16 samples")
    ap.add_argument("--bara-bilder", default="")
    ns = ap.parse_args()

    cfg: dict = {}
    src = Path(ns.effekt)
    if src.suffix == ".json":
        cfg = json.loads((src if src.exists() else HERE / src).read_text(encoding="utf-8"))
    else:
        cfg["effekt"] = ns.effekt
    for kv in ns.set:
        k, v = kv.split("=", 1)
        try:
            cfg[k] = json.loads(v)
        except json.JSONDecodeError:
            cfg[k] = v
    if ns.test:
        cfg.setdefault("scale", 50); cfg.setdefault("samples", 16)
    out = Path(ns.out).resolve(); frames = out / "frames"
    if frames.exists():
        shutil.rmtree(frames)                       # aldrig blanda gamla och nya bildrutor
    cfg["out"] = str(frames)
    if ns.bara_bilder:
        cfg["only_frames"] = [int(x) for x in ns.bara_bilder.split(",")]

    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1",
                        "-P", str(HERE / "blender3d.py"), "--", json.dumps(cfg, ensure_ascii=False)])
    if r.returncode:
        print("Blender avbröt (exitkod", r.returncode, ") – se STOPP-raden ovan.")
        return r.returncode
    qa = json.loads((frames / "qa.json").read_text(encoding="utf-8"))
    shutil.move(str(frames / "qa.json"), out / "qa.json")
    pngs = sorted(frames.glob("f_*.png"))
    scale = cfg.get("scale", 100) / 100
    if not cfg.get("only_frames"):
        safe_zones(qa, frames, scale)
        (out / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding="utf-8")
    w, h = round(1080 * scale), round(1920 * scale)
    sx0, sy0, sx1, sy1 = (round(v * scale) for v in qa["safe_zone"])
    guides = (f"drawbox=x={sx0}:y=0:w=2:h={h}:color=red,drawbox=x={sx1}:y=0:w=2:h={h}:color=red,"
              f"drawbox=x=0:y={sy0}:w={w}:h=2:color=red,drawbox=x=0:y={sy1}:w={w}:h=2:color=red")

    # Kontrollark: 4 bildrutor (mitt i rörelsen, landning, mitt i vilan, sista) på magenta.
    n = qa["frames"]
    pick = [p for p in pngs] if cfg.get("only_frames") else \
        [frames / f"f_{f:04d}.png" for f in sorted({max(1, qa["settle"] // 3), qa["settle"], (qa["settle"] + n) // 2, n})]
    inputs, chains = [], []
    for i, p in enumerate(pick[:4]):
        inputs += ["-i", str(p)]
        chains.append(f"color=c=0xff00ff:s={w}x{h}[m{i}];[m{i}][{i}:v]overlay,{guides}[c{i}]")
    fc = ";".join(chains)
    if len(chains) > 1:
        fc += ";" + "".join(f"[c{i}]" for i in range(len(chains))) + f"hstack=inputs={len(chains)}[c0]"
    ff(*inputs, "-filter_complex", fc, "-map", "[c0]", "-frames:v", "1", str(out / "kontroll-magenta.png"))
    if cfg.get("only_frames"):
        print("Stillbilder klara:", out / "kontroll-magenta.png"); return 0

    name = out.name
    seq = ["-framerate", str(qa["fps"]), "-i", str(frames / "f_%04d.png")]
    ff(*seq, "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0",
       str(out / f"{name}.mov"))
    ff(*seq, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28", "-row-mt", "1",
       "-auto-alt-ref", "0", str(out / f"{name}.webm"))
    ff("-f", "lavfi", "-i", f"color=c={BG}:s={w}x{h}:r={qa['fps']}", *seq, "-filter_complex",
       "[0][1]overlay=shortest=1,format=yuv420p", "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart",
       str(out / f"{name}-forhand.mp4"))

    # Leveranskontroll: avkoda allt, räkna bildrutor, kontrollera att alfan finns kvar i WebM (libvpx-avkodaren).
    fel = []
    for f, dec in ((f"{name}.mov", []), (f"{name}.webm", ["-c:v", "libvpx-vp9"]), (f"{name}-forhand.mp4", [])):
        p = subprocess.run(["ffprobe", "-v", "error", *dec, "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames,pix_fmt", "-of", "json", str(out / f)], capture_output=True, text=True)
        s = json.loads(p.stdout or "{}").get("streams", [{}])[0]
        got = int(s.get("nb_read_frames", 0))
        print(f"  {f}: {got} bildrutor, {s.get('pix_fmt')}")
        if got != n:
            fel.append(f"{f}: {got} bildrutor, väntade {n}")
    a = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(out / f"{name}.webm"), "-vf",
                        f"select=eq(n\\,{n - 1}),alphaextract,signalstats,metadata=print:file=-",
                        "-f", "null", "-"], capture_output=True, text=True)
    stats = dict(line.split("=", 1) for line in a.stdout.split() if "signalstats.Y" in line)
    if not (stats.get("lavfi.signalstats.YMIN") == "0" and stats.get("lavfi.signalstats.YMAX") == "255"):
        # sista bildrutan ska ha både helt genomskinliga och helt täckande pixlar
        fel.append("WebM: alfan saknas eller är ofullständig i sista bildrutan")
    print("Safe zones:", "OK" if qa["safe_ok"] else "UTANFÖR – se qa.json", "| landar bildruta", qa["settle"])
    if "lasregel_s" in qa:
        print(f"Läsregel: '{qa['text']}' behöver {qa['lasregel_s']} s, står still {qa['stilla_s']} s")
    for f in fel:
        print("FEL:", f)
    print("Klart:", out)
    return 1 if fel or not qa["safe_ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
