"""Generate the AI background for each carousel slide (PAID) via kie.ai.

Per slide: kie.ai Nano Banana Pro (image-to-image) with the carousel style
reference (+ optional per-slide subject image) -> styled 4:5 background -> download.
Needs your own KIE_API_KEY (see .env.example). Get one at https://kie.ai/api-key.

Idempotent: slides that already have a downloaded bg_file are skipped, so a
partially failed run can simply be re-run.

Usage: python carousel_generate.py <run_dir>
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import carousel_config as cfg
import kie_client as kie
import upload              # DISABLED stub: passes public URLs through, refuses local files


def _style_url() -> str:
    if cfg.STYLE_REFERENCE_URL:
        return cfg.STYLE_REFERENCE_URL
    if not cfg.STYLE_REFERENCE.exists():
        raise SystemExit(
            f"Carousel style reference not found: {cfg.STYLE_REFERENCE}\n"
            f"Drop your reference slide there (assets/carousel-style-reference.jpg), "
            f"and set CAROUSEL_STYLE_REFERENCE_URL (a PUBLIC url you host) in the repo-root .env."
        )
    return upload.public_url(cfg.STYLE_REFERENCE)


def _subject_url(slide: dict):
    """Optional second input image (the 'content' image) for this slide."""
    s = slide.get("subject_image")
    if not s:
        return None
    if str(s).startswith("http"):
        return s
    p = Path(s)
    if not p.is_absolute():
        p = cfg.CAROUSEL_ROOT / s
    if not p.exists():
        raise SystemExit(f"[slide {slide['index']}] subject_image not found: {p}")
    return upload.public_url(p)


def _process(slide: dict, style_url: str, media_dir: Path) -> dict:
    idx = slide["index"]
    bg = media_dir / f"slide{idx:02d}.png"

    if slide.get("bg_file") and bg.exists():
        print(f"[slide {idx}] bg exists, skipping")
        return slide

    inputs = [style_url]
    su = _subject_url(slide)
    if su:
        inputs.append(su)

    inp = {
        "prompt": slide["image_prompt"],
        "image_input": inputs,               # kie Nano Banana Pro: array of public image URLs
        "aspect_ratio": cfg.BG_ASPECT,       # "4:5" (native)
        "resolution": cfg.BG_RESOLUTION,     # 1K | 2K | 4K
        "output_format": "png",
    }
    print(f"[slide {idx}] generating background ({cfg.MODEL_IMAGE})"
          f"{' + subject' if su else ''}")
    url = kie.run(cfg.MODEL_IMAGE, inp, label=f"slide{idx}:bg")
    slide["bg_url"] = url
    kie.download(url, bg)
    slide["bg_file"] = str(bg)
    print(f"[slide {idx}] bg -> {bg}")
    return slide


def generate(run_dir):
    run_dir = Path(run_dir)
    plan_path = run_dir / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    if not cfg.KIE_API_KEY:
        raise SystemExit("Missing KIE_API_KEY — put it in a .env file at your project root "
                         "(KIE_API_KEY=...). Get a key at https://kie.ai/api-key.")

    style_url = _style_url()
    print(f"style reference URL: {style_url}")

    slides = plan["slides"]
    errors = []
    with ThreadPoolExecutor(max_workers=cfg.WORKERS) as ex:
        futs = {ex.submit(_process, s, style_url, media_dir): s["index"] for s in slides}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                fut.result()
            except Exception as e:  # noqa: BLE001 - collect + report all slide errors
                print(f"[slide {i}] ERROR: {e}")
                errors.append((i, str(e)))
            plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")  # persist after each

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    if errors:
        print(f"\n{len(errors)} slide(s) failed: {[e[0] for e in errors]}. "
              f"Re-run this command to retry only the failed slides.")
        raise SystemExit(1)
    print(f"\nAll {len(slides)} backgrounds generated -> {media_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python carousel_generate.py <run_dir>")
        raise SystemExit(1)
    generate(sys.argv[1])
