"""Config for the Instagram Carousel Generator (content-engine import, Windows-adapted).

Layout in the content-engine repo:
    library/kits/<kit>/carousel/        this runtime folder (scripts, templates, assets, knowledge)
    work/<kit>/                         everything generated: runs/, output/, photos/, shots/,
                                        logos/, my-images/, profile.json  (gitignored)
    .env (repo root)                    optional KIE_API_KEY for the PAID path

Free path (local painter / own photos / Wikimedia photos + Playwright render) is the default.
The paid kie.ai path needs KIE_API_KEY and costs credits.
"""
from __future__ import annotations

import os
from pathlib import Path

CAROUSEL_ROOT = Path(__file__).resolve().parent.parent   # library/kits/<kit>/carousel
KIT_DIR = CAROUSEL_ROOT.parent                             # library/kits/<kit>
KIT_NAME = KIT_DIR.name


def _find_repo_root() -> Path:
    for p in CAROUSEL_ROOT.parents:
        if (p / "library" / "README.md").exists() and (p / "library" / "kits").is_dir():
            return p
    return KIT_DIR


REPO_ROOT = _find_repo_root()
PROJECT_ROOT = REPO_ROOT                                   # where .env lives

# Load KIE_API_KEY (and other vars) from a .env file if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    for _env in (REPO_ROOT / ".env", KIT_DIR / ".env", CAROUSEL_ROOT / ".env"):
        if _env.exists():
            load_dotenv(_env)
            break
except Exception:
    pass  # dotenv optional; env vars still work

# --- Paths ---
ASSETS_DIR = CAROUSEL_ROOT / "assets"
KNOWLEDGE_DIR = CAROUSEL_ROOT / "knowledge"
WORK_DIR = Path(os.getenv("CAROUSEL_WORK_DIR") or (REPO_ROOT / "work" / KIT_NAME))
RUNS_DIR = WORK_DIR / "runs"
OUTPUT_DIR = WORK_DIR / "output"
PHOTOS_DIR = WORK_DIR / "photos"          # fetch_photos.py default target
SHOTS_DIR = WORK_DIR / "shots"            # capture.py screenshots
LOGOS_DIR = WORK_DIR / "logos"            # fetch_logo.py / your own logo files
MY_IMAGES_DIR = WORK_DIR / "my-images"    # own-photo sets (import_images.py)
PROFILE_FILE = WORK_DIR / "profile.json"
TEMPLATE = CAROUSEL_ROOT / "scripts" / "template.html"
# The single bundled style reference (only used by the PAID path).
STYLE_REFERENCE = ASSETS_DIR / "carousel-style-reference.jpg"

# --- Brand defaults (override per plan with "handle" / "brand_label" / "tagline",
#     on `carousel_run.py init --handle ... --brand ...`, or via env) ---
DEFAULT_HANDLE = os.getenv("CAROUSEL_HANDLE", "@golfkuponger")
DEFAULT_BRAND = os.getenv("CAROUSEL_BRAND", "Golfkuponger")
DEFAULT_TAGLINE = os.getenv("CAROUSEL_TAGLINE", "golfkuponger.se")

# --- Output canvas: Instagram carousel 4:5 (1080x1350) ---
CANVAS_W = int(os.getenv("CAROUSEL_W", "1080"))
CANVAS_H = int(os.getenv("CAROUSEL_H", "1350"))
RENDER_SCALE = int(os.getenv("CAROUSEL_RENDER_SCALE", "2"))

# --- PAID: background generation via kie.ai (bring your own KIE_API_KEY) ---
KIE_API_KEY = os.getenv("KIE_API_KEY", "")                 # https://kie.ai/api-key
KIE_BASE_URL = os.getenv("KIE_BASE_URL", "https://api.kie.ai")
MODEL_IMAGE = os.getenv("CAROUSEL_MODEL", "nano-banana-pro")
BG_ASPECT = os.getenv("CAROUSEL_BG_ASPECT", "4:5")
BG_RESOLUTION = os.getenv("CAROUSEL_BG_RESOLUTION", "2K")   # 1K | 2K | 4K
WORKERS = int(os.getenv("CAROUSEL_WORKERS", "3"))
# kie.ai only accepts PUBLIC image URLs. The original kit auto-uploaded your local style
# sheet / logo / subject photo to catbox.moe or 0x0.st — that was REMOVED in this import.
# Host the image yourself and set its URL here (or use URLs directly in plan.json).
STYLE_REFERENCE_URL = os.getenv("CAROUSEL_STYLE_REFERENCE_URL", "")

# --- Polling (kie) ---
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "6"))
POLL_TIMEOUT = float(os.getenv("POLL_TIMEOUT", "900"))

# --- Browser: Playwright's Chromium, falling back to the system Chrome ---
CHROME_PATHS = [
    os.getenv("CAROUSEL_CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def launch_browser(pw):
    """Plain headless Chromium (no fingerprint tricks). Falls back to the installed Chrome
    if `python -m playwright install chromium` has not been run."""
    try:
        return pw.chromium.launch()
    except Exception as first:  # noqa: BLE001
        for exe in CHROME_PATHS:
            if exe and Path(exe).exists():
                return pw.chromium.launch(executable_path=exe)
        raise first


def resolve(path) -> Path | None:
    """Resolve an asset path from plan.json: absolute, or relative to (in order) the kit's
    carousel/ folder, work/<kit>/, the repo root, or the current directory."""
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    for base in (CAROUSEL_ROOT, WORK_DIR, REPO_ROOT, Path.cwd()):
        cand = base / p
        if cand.exists():
            return cand
    return CAROUSEL_ROOT / p


# Windows consoles default to cp1252; never crash on a stray non-Latin-1 character in a print.
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass
