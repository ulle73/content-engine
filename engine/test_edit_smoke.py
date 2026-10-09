from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from .edit.models import EditJob
from .models import CatalogProduct, Company, MediaAsset


class EditSmokeCommandTests(TestCase):
    def test_cuts_catalog_images_into_a_queued_job(self):
        user = get_user_model().objects.create_user("owner", password="x")
        company = Company.objects.create(owner=user, name="Golfkuponger")
        for n in range(3):
            CatalogProduct.objects.create(company=company, source="shopify_page", external_id=f"golfbanor/k{n}",
                                          name=f"Klubb {n}", image_urls=[f"https://golfkuponger.se/cdn/shop/files/gk-k{n}-01.jpg"])

        def fake_materialize(product, indexes=None):
            return [MediaAsset.objects.create(company=company, kind="image", origin="uploaded", provider="website",
                                              storage_backend="local", storage_key=f"t/{product.pk}.jpg",
                                              mime_type="image/jpeg", byte_size=10, width=1080, height=1920)]

        out = StringIO()
        with mock.patch("engine.product_catalog.materialize", side_effect=fake_materialize), \
                mock.patch.dict("os.environ", {"GITHUB_DISPATCH_TOKEN": ""}):
            call_command("edit_smoke", stdout=out)
        job = EditJob.objects.get()
        self.assertEqual(len(job.cut_spec["scenes"]), 3)
        self.assertIn("3 scener", out.getvalue())
