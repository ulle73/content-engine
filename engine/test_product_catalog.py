import io
import json
from unittest import mock

import httpx
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from . import product_catalog
from .models import CatalogProduct, Company, MediaAsset


def _png():
    out = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(out, "PNG")
    return out.getvalue()


WOO = [{
    "id": 2865, "name": "Lumen Tesla &amp; Model 3 Paket", "sku": "139102-TES3-PAK",
    "permalink": "https://faiv.se/produkt/lumen-tesla/", "short_description": "<p>Grillkit för Tesla</p>",
    "description": "", "prices": {"price": "659900", "currency_code": "SEK", "currency_minor_unit": 2},
    "categories": [{"name": "Grillkit"}],
    "images": [{"src": f"https://www.faiv.se/wp-content/uploads/{i}.png"} for i in range(6)]
    + [{"src": "https://evil.example/x.png"}],
}]
SHOPIFY = {"products": [{
    "id": 77, "title": "Bro Hof Slott", "handle": "bro-hof", "body_html": "<b>18 hål</b>", "product_type": "Golfbana",
    "tags": ["Stockholm"], "variants": [{"sku": "", "price": "395.00"}],
    "images": [{"src": "https://cdn.shopify.com/s/files/bro.png"}],
}]}


def _transport(routes):
    def handler(request):
        key = request.url.path
        if key in routes:
            body = routes[key]
            if isinstance(body, bytes):
                return httpx.Response(200, content=body, headers={"content-type": "image/png"})
            if request.url.params.get("page", "1") != "1":
                body = [] if isinstance(body, list) else {"products": []}
            return httpx.Response(200, content=json.dumps(body), headers={"content-type": "application/json"})
        return httpx.Response(404, headers={"content-type": "text/html"})
    return httpx.Client(transport=httpx.MockTransport(handler))


class ProductCatalogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", password="x")
        self.faiv = Company.objects.create(owner=self.user, name="FAIV", brand={"landing_url": "https://www.faiv.se"})
        self.gk = Company.objects.create(owner=self.user, name="Golfkuponger")

    def test_woocommerce_sync_keeps_all_own_image_urls_without_downloading(self):
        result = product_catalog.sync(self.faiv, client=_transport({"/wp-json/wc/store/v1/products": WOO}))
        self.assertEqual((result["source"], result["products"], result["image_urls"]), ("woocommerce", 1, 6))
        product = CatalogProduct.objects.get(company=self.faiv)
        self.assertEqual(product.name, "Lumen Tesla & Model 3 Paket")
        self.assertEqual((product.price, product.currency), ("6599", "SEK"))
        self.assertEqual(product.description, "Grillkit för Tesla")
        self.assertEqual(len(product.image_urls), 6)
        self.assertFalse(MediaAsset.objects.exists())

    def test_shopify_fallback_and_deactivation(self):
        client = _transport({"/products.json": SHOPIFY})
        product_catalog.sync(self.gk, client=client)
        product = CatalogProduct.objects.get(company=self.gk)
        self.assertEqual((product.source, product.url, product.price), ("shopify", "https://golfkuponger.se/products/bro-hof", "395.00"))
        self.assertEqual(product.categories, ["Golfbana", "Stockholm"])
        result = product_catalog.sync(self.gk, client=_transport({"/products.json": {"products": []}}))
        self.assertEqual(result["deactivated"], 1)
        self.assertEqual(product_catalog.search(self.gk, "bro"), [])

    def test_unknown_shop_raises(self):
        with self.assertRaises(product_catalog.CatalogError):
            product_catalog.sync(self.faiv, client=_transport({}))

    @mock.patch("engine.product_catalog.put", return_value="local")
    def test_materialize_downloads_only_chosen_images_once(self, put):
        product_catalog.sync(self.faiv, client=_transport({"/wp-json/wc/store/v1/products": WOO}))
        product = product_catalog.search(self.faiv, "tesla grillkit")[0]
        client = _transport({"/wp-content/uploads/1.png": _png()})
        assets = product_catalog.materialize(product, indexes=[1, 99], client=client)
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].ad_tags.roles, ["product"])
        self.assertEqual(assets[0].alt_text, product.name)
        again = product_catalog.materialize(product, indexes=[1], client=client)
        self.assertEqual(again[0].pk, assets[0].pk)
        self.assertEqual(put.call_count, 1)
        self.assertEqual(product_catalog.serialize(product)["asset_ids"], [str(assets[0].pk)])

    def test_sync_button(self):
        self.client.force_login(self.user)
        url = reverse("engine:sync_products", kwargs={"workspace_id": self.faiv.pk})
        with mock.patch("engine.product_catalog.sync", return_value={"products": 3, "image_urls": 9}) as sync:
            response = self.client.post(url)
        sync.assert_called_once()
        self.assertEqual(response.status_code, 302)


SITEMAP = '<sitemapindex><sitemap><loc>https://golfkuponger.se/sitemap_metaobject_pages_1.xml</loc></sitemap></sitemapindex>'
PAGES = ('<urlset><url><loc>https://golfkuponger.se/pages/golfbanor/ale-gk</loc></url>'
         '<url><loc>https://golfkuponger.se/pages/golfbanor/bro-gk</loc></url></urlset>')
ALE = ('<script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":[{"name":"Golfbanor"},'
       '{"name":"G\u00f6teborgsomr\u00e5det"},{"name":"Ale GK"}]}</script>'
       '<meta name="description" content="Spela Ale GK med Golfkuponger">'
       '<img src="//golfkuponger.se/cdn/shop/files/gk-ale-gk-01.jpg?v=1&width=800">'
       '<img src="//golfkuponger.se/cdn/shop/files/gk-ale-gk-02_ab12.webp">'
       '<img src="//golfkuponger.se/cdn/shop/files/gk-vale-gk-01.jpg">'
       '<img src="//golfkuponger.se/cdn/shop/files/gk-alingsas-gk-01.jpg">')


class ShopifyPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", password="x")
        self.gk = Company.objects.create(owner=self.user, name="Golfkuponger")

    def _client(self, pages):
        def handler(request):
            path = request.url.path
            if path == "/products.json":
                body = SHOPIFY if request.url.params.get("page") == "1" else {"products": []}
                return httpx.Response(200, content=json.dumps(body), headers={"content-type": "application/json"})
            text = {"/sitemap.xml": SITEMAP, "/sitemap_metaobject_pages_1.xml": PAGES, **pages}.get(path)
            return httpx.Response(200, text=text) if text is not None else httpx.Response(404, text="")
        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_courses_become_catalog_entries_with_their_own_images(self):
        result = product_catalog.sync(self.gk, client=self._client({"/pages/golfbanor/ale-gk": ALE}))
        self.assertEqual((result["pages"], result["pages_fetched"]), (2, 1))
        ale = CatalogProduct.objects.get(company=self.gk, source="shopify_page")
        self.assertEqual(ale.name, "Ale GK")
        self.assertEqual(ale.categories, ["Golfbanor", "Göteborgsområdet"])
        self.assertEqual(ale.description, "Spela Ale GK med Golfkuponger")
        self.assertEqual(ale.image_urls, ["https://golfkuponger.se/cdn/shop/files/gk-ale-gk-01.jpg",
                                          "https://golfkuponger.se/cdn/shop/files/gk-ale-gk-02_ab12.webp"])
        self.assertEqual([p.name for p in product_catalog.search(self.gk, "golfbanor ale")], ["Ale GK"])

    def test_budget_and_fresh_pages_are_skipped(self):
        pages = {"/pages/golfbanor/ale-gk": ALE, "/pages/golfbanor/bro-gk": ALE.replace("Ale GK", "Bro GK")}
        first = product_catalog.sync(self.gk, client=self._client(pages), page_budget=1)
        self.assertEqual((first["pages_fetched"], first["pages_left"]), (1, 1))
        second = product_catalog.sync(self.gk, client=self._client(pages), page_budget=1)
        self.assertEqual((second["pages_fetched"], second["pages_left"]), (1, 0))
        third = product_catalog.sync(self.gk, client=self._client(pages))
        self.assertEqual(third["pages_fetched"], 0)
