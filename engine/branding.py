"""Official logo bytes are immutable sources, applied by Pillow rather than a generative model."""

import hashlib
import io
import re
from urllib.parse import urljoin, urlparse

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


# ---------------------------------------------------------------- fetching the logo from the company's own website

LOGO_MAX_BYTES = 5 * 1024 * 1024
_IMG = re.compile(r"<img\b[^>]*>", re.I)
_ATTR = re.compile(r'([a-zA-Z-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')


def company_site(company) -> str:
    """https://host of the company's own website (brand landing_url / shop_url), or ""."""
    from .motion.brand import landing_url

    kit = company.brand if isinstance(company.brand, dict) else {}
    url = kit.get("shop_url") or landing_url(company) or ""
    host = urlparse(url if "://" in url else f"https://{url}").hostname if url else None
    return f"https://{host}" if host else ""


def _same_site(url: str, site: str) -> bool:
    host, own = (urlparse(url).hostname or "").lower(), (urlparse(site).hostname or "").lower()
    strip = lambda h: h[4:] if h.startswith("www.") else h  # noqa: E731
    return bool(host) and strip(host) == strip(own)


def discover_logos(company, html: str, site: str) -> list[dict]:
    """Logo candidates on the company's homepage, best first: {"url", "score", "width", "height", "why"}.

    An <img> counts when its id/class/src/alt mentions "logo"; it scores for being marked as the site logo (id/class),
    for carrying the company's name, for sitting early in the page (the header) and for being on the company's own
    host. Partner and supplier logos further down score low."""
    name = re.sub(r"[^a-z0-9]", "", company.name.lower())
    out = []
    for match in _IMG.finditer(html):
        attrs = {k.lower(): (a or b) for k, a, b in _ATTR.findall(match.group(0))}
        src = urljoin(site + "/", attrs.get("src") or attrs.get("data-src") or "")
        marks = " ".join(attrs.get(k, "") for k in ("id", "class", "alt", "title")).lower()
        if "logo" not in marks + src.lower() or not src.startswith("http"):
            continue
        score, why = 0.0, []
        if "logo" in attrs.get("id", "").lower() or "logo" in attrs.get("class", "").lower():
            score += 6
            why.append("markerad som sidans logga")
        # The file name and alt/title, not the host: every image on faiv.se carries "faiv" in its URL.
        flat = re.sub(r"[^a-z0-9]", "", (urlparse(src).path.rsplit("/", 1)[-1] + " " + marks).lower())
        if name and name in flat:
            score += 4
            why.append("bolagets namn")
        if match.start() < len(html) * 0.25:
            score += 2
            why.append("i sidhuvudet")
        if not _same_site(src, site):
            score -= 6
        try:
            width, height = int(attrs.get("width") or 0), int(attrs.get("height") or 0)
        except ValueError:
            width = height = 0
        out.append({"url": src, "score": score, "width": width, "height": height, "why": ", ".join(why)})
    unique = {c["url"]: c for c in sorted(out, key=lambda c: c["score"])}
    return sorted(unique.values(), key=lambda c: (-c["score"], -(c["width"] * c["height"])))


def fetch_logo(company, url: str | None = None, *, client=None, dry_run: bool = False) -> dict:
    """Find (or take `url`) and download the company's logo from its own website and make it the official logo.

    Only files on the company's own host are taken unless a url is given explicitly. Returns {"url", "asset",
    "width", "height", "candidates", "warning"}; raises MediaError when nothing usable is found."""
    import httpx

    from .media import describe_file

    site = company_site(company)
    own = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True,
                                    headers={"User-Agent": "ContentEngine/1.0 (+logo for the site owner)"})
    try:
        candidates = []
        if not url:
            if not site:
                raise MediaError("Bolaget saknar webbadress (landing_url eller shop_url i varumärket).")
            page = client.get(site + "/")
            if page.status_code != 200:
                raise MediaError(f"{site} svarade {page.status_code}.")
            candidates = discover_logos(company, page.text, site)
            candidates = [c for c in candidates if c["score"] > 0]
            if not candidates:
                raise MediaError(f"Hittade ingen logga på {site}. Ange adressen till loggan.")
            url = candidates[0]["url"]
        response = client.get(url)
        data = response.content
        if response.status_code != 200 or not data or len(data) > LOGO_MAX_BYTES:
            raise MediaError(f"Loggan kunde inte hämtas från {url} ({response.status_code}).")
        info = describe_file(data)
        if info["kind"] != "image":
            raise MediaError("Loggan ska vara PNG, WebP eller JPEG.")
        warning = ""
        if (info.get("width") or 0) < 400:
            warning = (f"Loggan är bara {info.get('width')}×{info.get('height')} px; videon visar den högst 2× så stor. "
                       "En större PNG eller SVG-export från den som gjort loggan ger skarpare slutbild.")
        asset = None if dry_run else replace_logo(company, data, urlparse(url).path.rsplit("/", 1)[-1] or "logo")
        return {"url": url, "asset": asset, "width": info.get("width"), "height": info.get("height"),
                "candidates": candidates[:5], "warning": warning}
    except httpx.HTTPError as exc:
        raise MediaError(f"Webbplatsen kunde inte nås: {exc}") from exc
    finally:
        if own:
            client.close()
