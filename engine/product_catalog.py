"""Product catalog synced from the company's own webshop.

Supported: WooCommerce Store API (`/wp-json/wc/store/v1/products`), Shopify (`/products.json`) and
Shopify metaobject pages listed in the sitemap (Golfkuponger's golf courses, `/pages/golfbanor/<klubb>`).
Only the company's own shop domain (brand kit `shop_url`, else `landing_url`) is ever fetched.

The sync stores product data and *all* image URLs, never the image files: a full catalog would be
gigabytes. An image is downloaded into the media bank (role "product") only when a production
actually uses it, via `materialize`. Re-running is idempotent: the same image URL maps to the same
MediaAsset.
"""

from __future__ import annotations

import hashlib
import html
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlparse

import httpx
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .media import describe_file
from .media_storage import MediaError, put
from .models import CatalogProduct, MediaAsset

USER_AGENT = "ContentEngine/1.0 (+product sync for the shop owner)"
IMAGE_HOSTS_EXTRA = {"cdn.shopify.com"}
MAX_PRODUCTS = 5000
PAGE_REFRESH = timedelta(days=7)
PAGE_WORKERS = 6
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class CatalogError(ValueError):
    pass


def shop_url(company) -> str:
    from .motion.brand import landing_url

    kit = company.brand if isinstance(company.brand, dict) else {}
    url = kit.get("shop_url") or landing_url(company)
    if not url:
        raise CatalogError("Ange webbadress (eller shop_url) i bolagets varumärke först.")
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise CatalogError("Webbadressen är ogiltig.")
    return f"https://{parsed.hostname}"


def _host_root(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def _allowed_image(url: str, shop_host: str) -> bool:
    host = urlparse(url).hostname or ""
    return urlparse(url).scheme == "https" and (_host_root(host) == _host_root(shop_host) or host in IMAGE_HOSTS_EXTRA)


def _text(value: str, limit: int = 4000) -> str:
    plain = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", plain).strip()[:limit]


def _woocommerce(client, base) -> list[dict] | None:
    out, page = [], 1
    while len(out) < MAX_PRODUCTS:
        response = client.get(f"{base}/wp-json/wc/store/v1/products", params={"per_page": 100, "page": page})
        if response.status_code != 200 or "json" not in response.headers.get("content-type", ""):
            return None if page == 1 else out
        rows = response.json()
        if not rows:
            break
        for row in rows:
            prices = row.get("prices") or {}
            minor = int(prices.get("currency_minor_unit") or 0)
            raw = prices.get("price") or ""
            price = f"{int(raw) / 10 ** minor:g}" if str(raw).isdigit() else ""
            out.append({
                "external_id": str(row["id"]), "name": html.unescape(row.get("name", ""))[:300], "sku": row.get("sku", "")[:120],
                "url": row.get("permalink", "")[:500], "price": price, "currency": prices.get("currency_code", ""),
                "description": _text((row.get("short_description") or "") + " " + (row.get("description") or "")),
                "categories": [c.get("name", "") for c in row.get("categories", [])][:10],
                "image_urls": [i.get("src") for i in row.get("images", []) if i.get("src")],
            })
        if len(rows) < 100:
            break
        page += 1
    return out


def _shopify(client, base) -> list[dict] | None:
    out, page = [], 1
    while len(out) < MAX_PRODUCTS:
        response = client.get(f"{base}/products.json", params={"limit": 250, "page": page})
        if response.status_code != 200 or "json" not in response.headers.get("content-type", ""):
            return None if page == 1 else out
        rows = response.json().get("products", [])
        if not rows:
            break
        for row in rows:
            variant = (row.get("variants") or [{}])[0]
            out.append({
                "external_id": str(row["id"]), "name": row.get("title", "")[:300], "sku": (variant.get("sku") or "")[:120],
                "url": f"{base}/products/{row.get('handle', '')}"[:500], "price": variant.get("price") or "", "currency": "",
                "description": _text(row.get("body_html") or ""),
                "categories": [c for c in [row.get("product_type"), *(row.get("tags") or [])] if c][:10],
                "image_urls": [i.get("src") for i in row.get("images", []) if i.get("src")],
            })
        if len(rows) < 250:
            break
        page += 1
    return out


def fetch_products(company, *, client=None) -> tuple[str, list[dict]]:
    base = shop_url(company)
    own = client is None
    client = client or _client()
    try:
        for source, reader in (("woocommerce", _woocommerce), ("shopify", _shopify)):
            products = reader(client, base)
            if products is not None:
                return source, products
        # Say what the shop answered, so a block (e.g. bot protection against cloud IPs) is visible.
        answers = []
        for path in ("/wp-json/wc/store/v1/products", "/products.json"):
            response = client.get(f"{base}{path}")
            answers.append(f"{path} → {response.status_code} {response.headers.get('content-type', '?').split(';')[0]}")
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise CatalogError(f"Kunde inte läsa produkter från {base}: {exc}") from exc
    finally:
        if own:
            client.close()
    raise CatalogError("Hittade varken WooCommerce- eller Shopify-produkter på webbadressen ("
                       + "; ".join(answers) + ").")


def _image_asset(company, url, *, client, alt_text, tags) -> MediaAsset | None:
    asset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{company.pk}:{url}")
    existing = MediaAsset.objects.filter(pk=asset_id, company=company).first()
    if existing:
        return existing
    try:
        response = client.get(url)
    except httpx.HTTPError:
        return None
    if response.status_code != 200 or len(response.content) > MAX_IMAGE_BYTES:
        return None
    data = response.content
    try:
        metadata = describe_file(data)
    except MediaError:
        return None
    if metadata["kind"] != "image":
        return None
    key = f"{company.pk}/{asset_id}.{metadata.pop('extension')}"
    backend = put(key, data, metadata["mime_type"])
    asset = MediaAsset.objects.create(
        pk=asset_id, company=company, storage_backend=backend, storage_key=key, byte_size=len(data),
        origin="uploaded", provider="website", alt_text=alt_text[:500], purpose="content",
        sha256=hashlib.sha256(data).hexdigest(), **metadata)
    from .ad_studio.models import AssetTags

    AssetTags.objects.update_or_create(asset=asset, defaults={
        "description": alt_text[:500], "tags": tags[:12], "roles": ["product"], "theme": "produkt",
        "source": f"Produktbild från {urlparse(url).hostname}"})
    return asset


def _client():
    return httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT})


def _attr(page: str, pattern: str) -> str:
    match = re.search(pattern, page, re.S | re.I)
    return html.unescape(match.group(1)).strip() if match else ""


def page_urls(client, base) -> list[str]:
    """Every metaobject page (e.g. golf course) the shop lists in its sitemap."""
    urls = []
    try:
        index = client.get(f"{base}/sitemap.xml")
        if index.status_code != 200:
            return []
        for sitemap in re.findall(r"<loc>([^<]*sitemap_metaobject_pages[^<]*)</loc>", index.text):
            response = client.get(html.unescape(sitemap))
            if response.status_code == 200:
                urls += re.findall(r"<loc>([^<]+)</loc>", response.text)
    except httpx.HTTPError as exc:
        raise CatalogError(f"Kunde inte läsa sitemap från {base}: {exc}") from exc
    root = _host_root(urlparse(base).hostname)
    return list(dict.fromkeys(u for u in urls if _host_root(urlparse(u).hostname or "") == root))[:MAX_PRODUCTS]


def _page_id(url: str) -> str:
    return urlparse(url).path.strip("/")[:100]


def read_page(client, url) -> dict | None:
    """Name, breadcrumb categories, description and own images (file name contains the page handle)."""
    try:
        response = client.get(url)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    page = response.text
    handle = _page_id(url).rsplit("/", 1)[-1].lower()
    crumbs = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        if '"BreadcrumbList"' in block:
            crumbs = [html.unescape(name) for name in re.findall(r'"name":"([^"]+)"', block)]
    title = _attr(page, r'<meta\s+property="og:title"\s+content="([^"]*)"') or _attr(page, r"<title>(.*?)</title>")
    name = crumbs[-1] if crumbs else title.split("|")[0].strip() or handle
    parsed = urlparse(url)
    images = []
    for filename in re.findall(r'/cdn/shop/files/([^"\'\s?]+)', page):
        stem = filename.rsplit(".", 1)[0].lower()
        if re.search(rf"(^|[-_]){re.escape(handle)}([-_]|$)", stem):
            images.append(f"https://{parsed.hostname}/cdn/shop/files/{filename}")
    return {
        "external_id": _page_id(url), "name": name[:300], "sku": "", "url": url[:500], "price": "", "currency": "",
        "description": _text(_attr(page, r'<meta\s+(?:name="description"|property="og:description")\s+content="([^"]*)"')),
        "categories": crumbs[:-1][:10], "image_urls": list(dict.fromkeys(images)),
    }


def _upsert(company, source, items, base_host) -> int:
    created = 0
    for item in items:
        urls = list(dict.fromkeys(u for u in item.pop("image_urls") if _allowed_image(u, base_host)))
        with transaction.atomic():
            _, was_created = CatalogProduct.objects.update_or_create(
                company=company, source=source, external_id=item["external_id"],
                defaults={**item, "image_urls": urls, "active": True})
        created += was_created
    return created


def _deactivate(company, source, keep_ids) -> int:
    return (CatalogProduct.objects.filter(company=company, source=source, active=True)
            .exclude(external_id__in=keep_ids).update(active=False))


def sync(company, *, client=None, page_budget=None) -> dict:
    """Upsert product data + image URLs (no downloads). Products gone from the shop become inactive.

    On Shopify the sitemap's metaobject pages (Golfkuponger's golf courses) are read too. Pages synced within
    PAGE_REFRESH are skipped and at most `page_budget` stale pages are fetched per call (None = all), so the web
    button stays fast while the daily command fetches everything.
    """
    base = shop_url(company)
    base_host = urlparse(base).hostname
    own = client is None
    client = client or _client()
    try:
        source, products = fetch_products(company, client=client)
        created = _upsert(company, source, products, base_host)
        deactivated = _deactivate(company, source, [p["external_id"] for p in products])
        result = {"source": source, "pages": 0, "pages_fetched": 0, "pages_left": 0}
        if source == "shopify":
            urls = page_urls(client, base)
            fresh = set(CatalogProduct.objects.filter(
                company=company, source="shopify_page", active=True, synced_at__gte=timezone.now() - PAGE_REFRESH,
            ).values_list("external_id", flat=True))
            stale = [u for u in urls if _page_id(u) not in fresh]
            batch = stale if page_budget is None else stale[:page_budget]
            with ThreadPoolExecutor(PAGE_WORKERS) as pool:
                pages = [p for p in pool.map(lambda u: read_page(client, u), batch) if p]
            created += _upsert(company, "shopify_page", pages, base_host)
            if urls:
                deactivated += _deactivate(company, "shopify_page", [_page_id(u) for u in urls])
            result.update(pages=len(urls), pages_fetched=len(pages), pages_left=len(stale) - len(batch))
    finally:
        if own:
            client.close()
    active = CatalogProduct.objects.filter(company=company, active=True)
    return dict(result, products=active.count(), created=created, deactivated=deactivated,
                image_urls=sum(len(urls) for urls in active.values_list("image_urls", flat=True)),
                synced_at=timezone.now().isoformat())


def search(company, query="", *, limit=20):
    """Find active products by name, SKU, category or description words."""
    products = CatalogProduct.objects.filter(company=company, active=True)
    for word in (query or "").split():
        products = products.filter(Q(name__icontains=word) | Q(sku__icontains=word) | Q(description__icontains=word) | Q(categories__icontains=word))
    return list(products[:limit])


def materialize(product, *, indexes=None, client=None) -> list[MediaAsset]:
    """Download the chosen product images (default: all) into the media bank, on demand."""
    urls = product.image_urls if indexes is None else [product.image_urls[i] for i in indexes if 0 <= i < len(product.image_urls)]
    tags = [t for t in [product.sku, *product.categories] if t]
    own = client is None
    client = client or _client()
    assets = []
    try:
        for url in urls:
            asset = _image_asset(product.company, url, client=client, alt_text=product.name, tags=tags)
            if asset:
                product.assets.add(asset)
                assets.append(asset)
    finally:
        if own:
            client.close()
    return assets


def serialize(product) -> dict:
    return {
        "product_id": product.pk, "name": product.name, "sku": product.sku, "url": product.url,
        "price": product.price, "currency": product.currency, "categories": product.categories,
        "description": product.description[:600], "image_urls": product.image_urls,
        "asset_ids": [str(pk) for pk in product.assets.values_list("pk", flat=True)],
    }
