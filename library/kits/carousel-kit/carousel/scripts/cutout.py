"""Cut the subject out of a photo (transparent PNG), free and offline — Windows port.

The original kit compiled an Apple Vision helper (cutout.swift, macOS 14+ only). This import
replaces it with local, free engines that run on Windows:

  1. rembg            if installed in the library venv (general objects: people, trees, houses)
                      library/.venv/Scripts/python -m pip install "rembg[cpu]"
  2. hyperframes      `npx hyperframes remove-background` (u2net_human_seg — best on PEOPLE;
                      downloads ~168 MB of weights once)

The cutout is the same pixel size as the photo, so a template can stack
    photo  ->  headline  ->  cutout
and the headline reads as sitting BEHIND the subject (Sun-Faded, Sky-Blue, own-photo layouts).

Usage (from the repo root):
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/cutout.py <photo> [<out.png>]
    ... cutout.py <photo> <out.png> --mask              # alpha mask only (L8 PNG)
    ... cutout.py <photo> <out.png> --engine hyperframes   # force an engine (auto|rembg|hyperframes)
Default out: <photo>.cutout.png. Always LOOK at the cutout (e.g. on magenta) before using it.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _has_rembg() -> bool:
    try:
        import rembg  # noqa: F401
        return True
    except Exception:
        return False


def _npx() -> str | None:
    return shutil.which("npx") or shutil.which("npx.cmd")


def available() -> str | None:
    """Name of the engine that `auto` would use, or None if no engine is available."""
    if _has_rembg():
        return "rembg"
    if _npx():
        return "hyperframes"
    return None


def _rembg(photo: Path, out: Path):
    from PIL import Image
    from rembg import new_session, remove
    session = new_session("isnet-general-use")
    im = Image.open(photo).convert("RGB")
    cut = remove(im, session=session)
    cut.save(out)


def _hyperframes(photo: Path, out: Path):
    npx = _npx()
    if not npx:
        raise SystemExit("cutout: neither rembg nor npx found. Install Node (npx) or "
                         "`library/.venv/Scripts/python -m pip install \"rembg[cpu]\"`.")
    tmp = out.with_suffix(".hf.png")
    r = subprocess.run([npx, "--yes", "hyperframes", "remove-background", str(photo), "-o", str(tmp)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not tmp.exists():
        raise SystemExit(f"cutout failed for {photo.name}: {(r.stderr or r.stdout).strip()[-600:]}")
    tmp.replace(out)


def cutout(photo: str | Path, out: str | Path | None = None, mask: bool = False,
           engine: str = "auto") -> Path:
    from PIL import Image
    photo = Path(photo)
    out = Path(out) if out else photo.with_suffix(".cutout.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    eng = available() if engine == "auto" else engine
    if eng == "rembg":
        _rembg(photo, out)
    elif eng == "hyperframes":
        _hyperframes(photo, out)
    else:
        raise SystemExit("cutout: no background-removal engine available "
                         "(install rembg in library/.venv, or Node for `npx hyperframes`).")
    cut = Image.open(out).convert("RGBA")
    src = Image.open(photo)
    if cut.size != src.size:                       # guarantee same-size alignment
        cut = cut.resize(src.size, Image.LANCZOS)
    alpha = cut.getchannel("A")
    if not alpha.getbbox() or max(alpha.getextrema()) < 40:
        out.unlink(missing_ok=True)
        raise SystemExit(f"cutout: no foreground subject found in {photo.name} ({eng})")
    (alpha if mask else cut).save(out)
    n = sum(1 for v in alpha.resize((64, 64)).tobytes() if v > 128)
    print(f"{out}  ({eng}, subject ~{n / 40.96:.0f}% of frame)")
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); raise SystemExit(1)
    m = "--mask" in a
    eng = "auto"
    if "--engine" in a:
        i = a.index("--engine"); eng = a[i + 1]; del a[i:i + 2]
    a = [x for x in a if x != "--mask"]
    cutout(a[0], a[1] if len(a) > 1 else None, m, eng)
