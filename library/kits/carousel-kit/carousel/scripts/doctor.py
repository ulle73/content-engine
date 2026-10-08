"""Check (and with --fix, install) everything the carousel kit needs.

    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/doctor.py         # report
    library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/doctor.py --fix   # install into the venv

--fix only installs into an ACTIVE virtualenv (library/.venv), never globally / --user.

Required: Python 3.9+, Pillow, requests, python-dotenv, Playwright + its Chromium.
Optional: pillow-heif (iPhone HEIC photos),
          rembg in the venv or Node/npx (`npx hyperframes remove-background`) for subject cutouts,
          KIE_API_KEY in .env (only for the paid kie.ai path).
"""
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIP = {"PIL": "Pillow", "numpy": "numpy", "requests": "requests", "dotenv": "python-dotenv", "playwright": "playwright"}
OPTIONAL_PIP = {"pillow_heif": "pillow-heif"}


def _has(mod):
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def _chromium_ok() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import carousel_config as cfg
            cfg.launch_browser(p).close()
        return True
    except Exception:
        return False


def main(fix: bool):
    ok = True
    print(f"python      {sys.version.split()[0]}  {'ok' if sys.version_info >= (3, 9) else 'NEED 3.9+'}")
    missing = [pkg for mod, pkg in PIP.items() if not _has(mod)]
    opt_missing = [pkg for mod, pkg in OPTIONAL_PIP.items() if not _has(mod)]
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if fix and not in_venv:
        print("refusing --fix outside a virtualenv: run with library/.venv/Scripts/python")
        fix = False
    if fix and (missing or opt_missing):
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *missing, *opt_missing])
        importlib.invalidate_caches()
        missing = [pkg for mod, pkg in PIP.items() if not _has(mod)]
        opt_missing = [pkg for mod, pkg in OPTIONAL_PIP.items() if not _has(mod)]
    for mod, pkg in PIP.items():
        print(f"{pkg:14s}{'ok' if pkg not in missing else 'MISSING'}")
    ok &= not missing
    chrom = _has("playwright") and _chromium_ok()
    if fix and _has("playwright") and not chrom:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        chrom = _chromium_ok()
    print(f"{'chromium':14s}{'ok' if chrom else 'MISSING  (library/.venv/Scripts/python -m playwright install chromium)'}")
    ok &= chrom
    heic = not opt_missing
    print(f"{'heic':14s}{'ok' if heic else 'optional: pip install pillow-heif (in library/.venv)'}")
    cut = _has("rembg") and "rembg" or (shutil.which("npx") and "npx hyperframes remove-background")
    print(f"{'cutouts':14s}{('ok (' + cut + ')') if cut else 'optional: rembg in the venv, or Node/npx'}")
    env = next((p for p in (ROOT.parents[3] / ".env", ROOT.parent / ".env") if p.exists()), None)
    key = bool(os.getenv("KIE_API_KEY")) or (env and "KIE_API_KEY=" in env.read_text(encoding="utf-8")
                                              and "your_kie_ai_key_here" not in env.read_text(encoding="utf-8"))
    print(f"{'paid (kie)':14s}{'key found' if key else 'no key — free path only (fine)'}")
    print("\nREADY" if ok else "\nNOT READY — run: library/.venv/Scripts/python library/kits/carousel-kit/carousel/scripts/doctor.py --fix")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main("--fix" in sys.argv))
