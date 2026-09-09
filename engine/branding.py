"""Official logo bytes are immutable sources, applied by Pillow rather than a generative model."""

import hashlib
import io

from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps

from .media_storage import MediaError, open_asset
from .models import Company


def replace_logo(company, data, filename):
    from .media import describe_file, store_asset

    info = describe_file(data)
    if info["kind"] != "image":
        raise MediaError("Loggan ska vara PNG, WebP eller JPEG. Transparent PNG rekommenderas.")
    # Keep exactly the uploaded file. Replacing the pointer never overwrites an old version.
    with transaction.atomic():
        locked = Company.objects.select_for_update().get(pk=company.pk)
        digest = hashlib.sha256(data).hexdigest()
        if locked.official_logo_id and locked.official_logo.sha256 == digest:
            return locked.official_logo
        asset = store_asset(locked, data, alt_text=filename, purpose="logo")
        asset.used_at = timezone.now()
        asset.save(update_fields=["used_at"])
        locked.official_logo = asset
        locked.save(update_fields=["official_logo"])
        return asset


def read_logo(logo):
    with open_asset(logo) as file:
        original = file.read()
    if hashlib.sha256(original).hexdigest() != logo.sha256:
        raise MediaError("Loggans fil motsvarar inte den sparade officiella versionen. Kontrollera lagringen.")
    return original


def compose_logo(data, logo):
    """Use original pixels, proportional downscaling only, on a neutral corner panel."""
    with Image.open(io.BytesIO(data)) as image:
        canvas = ImageOps.exif_transpose(image).convert("RGBA")
    original = read_logo(logo)
    with Image.open(io.BytesIO(original)) as image:
        mark = ImageOps.exif_transpose(image).convert("RGBA")
    margin = max(8, round(min(canvas.size) * .025))
    mark.thumbnail((max(1, canvas.width // 4), max(1, canvas.height // 9)), Image.Resampling.LANCZOS)
    panel = Image.new("RGBA", (mark.width + margin, mark.height + margin), "white")
    panel.alpha_composite(mark, (margin // 2, margin // 2))
    canvas.alpha_composite(panel, (canvas.width-panel.width-margin, canvas.height-panel.height-margin))
    out = io.BytesIO()
    canvas.save(out, "PNG")
    return out.getvalue()
