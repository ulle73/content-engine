"""Deterministic quality and price review before the user confirms optimization.

Planning rates are dated hints. The existing provider's authenticated estimate
and approval fence remain mandatory before any paid media call.
"""
import io
from decimal import Decimal, InvalidOperation

from PIL import Image, ImageOps

from engine.creative_budget import SEEDANCE_25_PRICE_SOURCE, cost_ceiling, known_video_cost
from engine.media import store_asset
from engine.media_storage import open_asset

RATIOS = {"portrait": (9, 16), "square": (1, 1), "landscape": (16, 9)}


def review(spec, assets, candidate):
    shape = spec["options"]["shape"]
    x, y = RATIOS[shape]
    target_ratio = x / y
    checks, warnings = [], list(candidate.get("warnings", []))
    if spec["workflow"] in {"image", "video", "sequence"} and assets:
        warnings.append("Hela bilderna behålls i nya kopior med neutral bakgrund i valt format. Originalen sparas. Bakgrunden kan bli synlig i AI-filmen." if spec["options"].get("image_policy", "contain") == "contain" else "Nya kopior beskärs till valt format. Delar av motiven kan försvinna. Originalen sparas.")
    scene_ratios = []
    for position, (role, asset) in enumerate(assets.items(), 1):
        problems = []
        if asset.kind == "image":
            if not asset.width or not asset.height:
                problems.append("Upplösningen är inte verifierad. Byt fil innan du beställer ett skarpt resultat.")
            else:
                actual = asset.width / asset.height
                if role not in {"logo", "audio"}:
                    scene_ratios.append(actual)
                    if abs(actual / target_ratio - 1) > .05:
                        retained = min(actual / target_ratio, target_ratio / actual)
                        problems.append(f"Avviker från {x}:{y}. Fylls bilden helt kan cirka {round((1-retained)*100)} % beskäras. Behåll hela bilden för att undvika detta.")
                    target_width, target_height = (1080, round(1080 / target_ratio)) if target_ratio <= 1 else (1920, round(1920 / target_ratio))
                    scale = min(target_width / asset.width, target_height / asset.height)
                    if scale > 1.5:
                        problems.append(f"Liten för slutformatet ({target_width} × {target_height}). Cirka {scale:.1f}× förstoring kan bli suddig. Välj större original eller acceptera lägre skärpa.")
        checks.append({"asset_id": str(asset.pk), "position": position, "role": role.split(":")[0], "label": asset.alt_text or "Fil",
                       "kind": asset.kind, "width": asset.width, "height": asset.height, "warnings": problems})
    if scene_ratios and max(scene_ratios) / min(scene_ratios) > 1.05:
        warnings.append("Bilderna har olika proportioner. Samma utsnitt kan inte behållas automatiskt i alla övergångar. Förbered enhetliga start-/slutbilder i samma format innan AI-generation.")
    clips = candidate.get("clips", [candidate])
    prices = []
    for clip in clips:
        parameters = clip.get("parameters", {})
        amount = known_video_cost(clip.get("model_id"), parameters.get("duration", 0), parameters.get("resolution", "")) if spec["workflow"] in {"video", "sequence"} else None
        prices.append({"usd": str(amount) if amount is not None else None, "duration": parameters.get("duration"),
                       "resolution": parameters.get("resolution"), "model_label": clip.get("model_label", candidate.get("model_label", ""))})
        if parameters.get("resolution") == "480p":
            warnings.append("480p är ett ekonomiskt testformat. Så små videoklipp kan inte användas i den skarpa Motion-slutfilmen. Prova 4 sekunder per övergång i 720p, eller välj större original/upplösning inför slutfilmen.")
    local = spec["workflow"] in {"motion", "text"}
    total = Decimal("0") if local else sum((Decimal(row["usd"]) for row in prices), Decimal("0")) if all(row["usd"] is not None for row in prices) else None
    limit = Decimal(str(spec["options"].get("max_cost_usd", "5")))
    return {"model_label": candidate.get("model_label", ""), "parameters": candidate.get("parameters", {}),
            "image_policy": spec["options"].get("image_policy", "contain"), "assets": checks, "warnings": list(dict.fromkeys(warnings)),
            "clips": prices, "count": len(clips), "total_usd": str(total) if total is not None else None,
            "price_source": "Ingen ny AI-mediegeneration" if local else SEEDANCE_25_PRICE_SOURCE if total is not None else "Pris saknas för valda parametrar",
            "price_note": "Förslag utifrån tidigare kontopris. Aktuellt leverantörspris kontrolleras efter bekräftelsen, före betald start." if not local else "AI-samtalet debiteras separat. Motion renderas på din anslutna dator.",
            "max_cost_usd": str(limit), "over_budget": total is not None and total > limit,
            "recommendation": candidate.get("recommendation", {"model_label": candidate.get("model_label", ""), "reason": "Använder befintligt material och kräver ingen ny AI-mediegeneration."}),
            "max_per_clip_usd": str(cost_ceiling()) if not local else None}


def assert_budget(plan, job_ids):
    """Reserve the entire quoted order, under the conversation lock, before start."""
    from engine.models import MediaGeneration
    jobs = list(MediaGeneration.objects.select_for_update().filter(pk__in=job_ids, run__workspace=plan.turn.conversation.company).order_by("pk"))
    quote = budget_status(plan.spec, jobs, expected_count=len(job_ids))
    if not quote["verified"]:
        raise ValueError("Ett verifierat maxpris saknas. Betald start är stoppad tills priset kan säkerställas inom din budget.")
    if quote["over_budget"]:
        raise ValueError(f"Aktuellt totalpris ${quote['total_usd']} överstiger din maxkostnad ${quote['max_cost_usd']}. Ändra budget eller upplägg och skicka igen.")


def budget_status(spec, jobs, *, expected_count):
    total = Decimal("0")
    verified = len(jobs) == expected_count
    for job in jobs:
        amount = job.usage.get("approved_max_usd") or job.usage.get("estimate", {}).get("usd")
        try:
            amount = Decimal(str(amount))
        except InvalidOperation:
            verified = False
            continue
        if not amount.is_finite() or amount < 0:
            verified = False
            continue
        total += amount
    limit = Decimal(str(spec["options"].get("max_cost_usd", "5")))
    return {"verified": verified, "total_usd": str(total) if verified else None, "max_cost_usd": str(limit), "over_budget": verified and total > limit}


def normalize_images(company, spec, assets):
    """Explicitly confirmed presentation policy; create copies, never overwrite originals."""
    if spec["workflow"] not in {"image", "video", "sequence"}:
        return assets, []
    x, y = RATIOS[spec["options"]["shape"]]
    size = (1080, round(1080 * y / x)) if x <= y else (1920, round(1920 * y / x))
    result, copies = dict(assets), []
    for role, asset in assets.items():
        if asset.kind != "image" or role in {"logo", "audio"} or (asset.width and asset.height and abs((asset.width / asset.height) / (x/y)-1) <= .005):
            continue
        with open_asset(asset) as file, Image.open(file) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            if spec["options"].get("image_policy", "contain") == "crop":
                output = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
            else:
                image.thumbnail(size, Image.Resampling.LANCZOS)
                output = Image.new("RGB", size, "#f1f3f2")
                output.paste(image, ((size[0]-image.width)//2, (size[1]-image.height)//2))
            stream = io.BytesIO()
            output.save(stream, format="PNG")
        copy = store_asset(company, stream.getvalue(), alt_text=(asset.alt_text[:420] + f" · {x}:{y} kopia"))
        copy.expires_at = asset.expires_at
        copy.save(update_fields=["expires_at"])
        result[role] = copy
        copies.append({"original_id": str(asset.pk), "asset_id": str(copy.pk), "policy": spec["options"].get("image_policy", "contain")})
    return result, copies
