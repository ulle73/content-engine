"""Brand outros (slutbilder): a finished end clip per company and format, appended to every cut.

Files live in edit-renderer/outros/<brand>/<variant>-<9x16|4x5|1x1|16x9>.mp4 (H.264 + AAC, the brand's original logo
sound untouched). The brand kit key `outro` picks the variant; "none" switches it off. Golfkuponger defaults to
"spotlight" (chosen by the owner 2026-10-09). When an outro applies it replaces the generic CTA end card.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "edit-renderer" / "outros"
DURATION_S = 4.0
DEFAULTS = {"golfkuponger": "spotlight"}
LABELS = {"spotlight": "Slutbild Spotlight (logo + ljud, texten skrivs fram)"}


def variant_for(company) -> str | None:
    from engine.motion import brand as brand_kit

    kit = company.brand if isinstance(company.brand, dict) else {}
    variant = kit.get("outro") or DEFAULTS.get(brand_kit.brand_id_for(company))
    return None if not variant or variant == "none" else variant


def available(brand_id: str) -> list[str]:
    folder = ROOT / brand_id
    return sorted({p.stem.rsplit("-", 1)[0] for p in folder.glob("*.mp4")}) if folder.is_dir() else []


def outro_for(company, fmt: str) -> dict | None:
    """{"id", "brand", "variant", "file" (relative to edit-renderer/), "duration_s", "label"} or None."""
    from engine.motion import brand as brand_kit

    variant = variant_for(company)
    if not variant:
        return None
    brand_id = brand_kit.brand_id_for(company)
    name = f"{variant}-{fmt.replace(':', 'x')}.mp4"
    if not (ROOT / brand_id / name).is_file():
        return None
    return {"id": f"outro.{brand_id}.{variant}", "brand": brand_id, "variant": variant,
            "file": f"outros/{brand_id}/{name}", "duration_s": DURATION_S,
            "label": LABELS.get(variant, f"Slutbild {variant}")}
