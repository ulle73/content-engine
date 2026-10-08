"""Import a user's OWN photos for an own-images carousel.

Takes any mix of files and folders (drag them into the terminal, or put them in
work/carousel-kit/my-images/inbox/), and for each photo:
  - converts HEIC/HEIF/PNG/WebP/TIFF to JPEG and applies the camera rotation (EXIF)
  - caps the long side at 3840px (sharp at the 2x render scale, small enough to embed)
  - cuts out the subject (scripts/cutout.py: rembg or `npx hyperframes remove-background`)
  - measures the subject box, which side of the frame is emptier, how busy the top
    and bottom are, and samples accent colours from the photo
and writes work/carousel-kit/my-images/<set>/manifest.json so Claude can pick a layout per photo.

Usage (from the repo root):
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/import_images.py <set-name> <file-or-folder> [...]
    ... import_images.py <set-name>            # uses work/carousel-kit/my-images/inbox/
    ... import_images.py <set-name> ... --no-cutout
Manifest paths (file, cutout) are relative to work/carousel-kit/ and resolve in plan.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import carousel_config as cfg                   # noqa: E402
ROOT = cfg.WORK_DIR                             # work/<kit>/ (paths in the manifest are relative to it)
MY = cfg.MY_IMAGES_DIR
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}
MAX_SIDE = 3840


def _open(path: Path):
    """PIL image, with HEIC support via pillow-heif (no macOS `sips` on Windows)."""
    from PIL import Image, ImageOps
    if path.suffix.lower() in (".heic", ".heif"):
        try:
            import pillow_heif  # type: ignore
            pillow_heif.register_heif_opener()
        except ImportError:
            raise SystemExit(f"Can't read {path.name}: install HEIC support with "
                             f"`library/.venv/Scripts/python -m pip install pillow-heif` "
                             f"(or export it as JPEG).")
    im = Image.open(path)
    return ImageOps.exif_transpose(im).convert("RGB")


def _gather(args: list[str]) -> list[Path]:
    out = []
    for a in args:
        p = Path(a).expanduser()
        if p.is_dir():
            # skip generated folders (cutouts) and hidden files
            out += sorted(q for q in p.rglob("*") if q.suffix.lower() in EXTS
                          and "cutouts" not in q.relative_to(p).parts and not q.name.startswith("."))
        elif p.suffix.lower() in EXTS and p.exists():
            out.append(p)
        else:
            print(f"skip (not an image or missing): {a}")
    return out


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(v) for v in rgb[:3])


def _analyse(img, cut_path: Path | None) -> dict:
    """Subject box, empty side, busy-ness, accent candidates — all in 0..1 units."""
    from PIL import Image, ImageFilter, ImageStat
    W, H = img.size
    info: dict = {"w": W, "h": H, "orientation": "portrait" if H > W * 1.05 else
                  "landscape" if W > H * 1.05 else "square"}
    subj = None
    if cut_path and cut_path.exists():
        a = Image.open(cut_path).getchannel("A")
        bb = a.point(lambda v: 255 if v > 40 else 0).getbbox()
        if bb:
            x0, y0, x1, y1 = bb
            subj = {"x0": round(x0 / W, 3), "y0": round(y0 / H, 3),
                    "x1": round(x1 / W, 3), "y1": round(y1 / H, 3),
                    "area": round(ImageStat.Stat(a).mean[0] / 255, 3)}
    info["subject"] = subj
    # busy-ness: edge energy per region (low = calm space for type)
    small = img.resize((120, round(120 * H / W)))
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES)
    ew, eh = edges.size

    def busy(box):
        x0, y0, x1, y1 = box
        return round(ImageStat.Stat(edges.crop((int(x0 * ew), int(y0 * eh), int(x1 * ew), int(y1 * eh)))).mean[0] / 255, 3)
    info["busy"] = {"top": busy((0, 0, 1, .35)), "bottom": busy((0, .65, 1, 1)),
                    "left": busy((0, 0, .45, 1)), "right": busy((.55, 0, 1, 1))}
    if subj and subj["x1"] - subj["x0"] > .8:
        info["empty_side"] = "none"          # subject fills the width: use top/bottom bands
    elif subj:
        cx = (subj["x0"] + subj["x1"]) / 2
        info["empty_side"] = "right" if cx < .45 else "left" if cx > .55 else "both"
    else:
        info["empty_side"] = "left" if info["busy"]["left"] < info["busy"]["right"] else "right"
    # accent candidates: most saturated clusters (the photo supplies the colour)
    q = small.convert("RGB").quantize(colors=12, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:36]
    counts = sorted(q.getcolors(), reverse=True)
    cands = []
    import colorsys
    for n, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        cands.append({"hex": _hex((r, g, b)), "share": round(n / (ew * eh), 3),
                      "sat": round(s, 2), "light": round(l, 2)})
    info["palette"] = cands
    # small but vivid things (a cone, a sign, a jacket) make the best accents, so look at
    # strongly saturated pixels directly and bin them by hue, not only at big clusters
    bins: dict = {}
    for r, g, b in small.convert("RGB").getdata():
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if s > .45 and .28 < l < .78:
            k = int(h * 12) % 12
            e = bins.setdefault(k, [0, 0, 0, 0]); e[0] += r; e[1] += g; e[2] += b; e[3] += 1
    total = ew * eh
    vivid = sorted(((e[3], _hex((e[0] / e[3], e[1] / e[3], e[2] / e[3]))) for e in bins.values()
                    if e[3] / total > .002), reverse=True)
    info["accent_candidates"] = [h for _, h in vivid][:3]
    return info


def main(argv: list[str]):
    if not argv:
        print(__doc__); raise SystemExit(1)
    no_cut = "--no-cutout" in argv
    argv = [a for a in argv if a != "--no-cutout"]
    set_name = re.sub(r"[^a-z0-9-]+", "-", argv[0].lower()).strip("-") or "my-set"
    srcs = _gather(argv[1:] or [str(MY / "inbox")])
    if not srcs:
        raise SystemExit("No images found. Drop photos into work/<kit>/my-images/inbox/ "
                         "or pass file/folder paths.")
    dest = MY / set_name
    (dest / "cutouts").mkdir(parents=True, exist_ok=True)
    man_path = dest / "manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {"set": set_name, "photos": []}
    have = {p["source"] for p in manifest["photos"]}
    import hashlib
    seen = {p.get("sha1") for p in manifest["photos"]}

    import cutout as _cutout
    can_cut = not no_cut and bool(_cutout.available())
    if not no_cut and not can_cut:
        print("note: subject cutouts need rembg in library/.venv or Node (`npx hyperframes "
              "remove-background`); continuing without them.")
    n0 = len(manifest["photos"])
    for src in srcs:
        sha1 = hashlib.sha1(src.read_bytes()).hexdigest()
        if str(src) in have or sha1 in seen:
            print(f"already imported: {src.name}"); continue
        seen.add(sha1)
        i = len(manifest["photos"]) + 1
        stem = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-")[:40] or "photo"
        out = dest / f"{i:02d}-{stem}.jpg"
        img = _open(src)
        if max(img.size) > MAX_SIDE:
            k = MAX_SIDE / max(img.size)
            from PIL import Image
            img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
        img.save(out, quality=92)
        cut = None
        if can_cut:
            try:
                import cutout
                png = cutout.cutout(out, dest / "cutouts" / f"{out.stem}.png")
                # WebP with alpha is ~7x smaller than PNG: faster to embed and render
                from PIL import Image
                cut = png.with_suffix(".webp")
                Image.open(png).save(cut, "WEBP", quality=90, method=4)
                png.unlink()
            except SystemExit as e:
                print(f"  no clean subject in {out.name} ({e}) — fine for editorial/punch layouts")
        info = _analyse(img, cut)
        manifest["photos"].append({
            "file": out.relative_to(ROOT).as_posix(), "source": str(src), "sha1": sha1,
            "cutout": cut.relative_to(ROOT).as_posix() if cut else None, **info})
        s = info["subject"]
        print(f"[{i}] {out.name}  {info['w']}x{info['h']} {info['orientation']}"
              f"  subject={'yes' if s else 'no'}  empty side={info['empty_side']}"
              f"  accents={','.join(info['accent_candidates']) or '-'}")
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(manifest['photos']) - n0} new photo(s) -> {dest}\nmanifest: {man_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
