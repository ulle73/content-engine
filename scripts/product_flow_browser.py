"""Isolated real-browser regression suite. No paid providers or production data.

Run: python scripts/product_flow_browser.py
Install test-only browser: pip install playwright==1.55.0 && python -m playwright install chromium
PRODUCT_FLOW_BASELINE=1 records the pre-composer behavior for comparison.
"""
import json
import os
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "engine.test_settings"
import django

django.setup()
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections
from django.test import override_settings
from django.test.runner import DiscoverRunner
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from playwright.sync_api import expect, sync_playwright

from engine.forms import snapshot_company_context
from engine.media import store_asset
from engine.models import Company, ContentRun, MediaGeneration

BASELINE = os.environ.get("PRODUCT_FLOW_BASELINE") == "1"
EVIDENCE = ROOT / "data" / "product-flow-browser" / ("before" if BASELINE else "after")
EVIDENCE.mkdir(parents=True, exist_ok=True)


class ProductFlowBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        storage = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(override_settings(MEDIA_STORAGE="local", MEDIA_ROOT=Path(storage)))
        self.user = get_user_model().objects.create_user(
            username="product-flow@example.invalid", email="product-flow@example.invalid", password="isolated-demo-only",
        )
        self.company = Company.objects.create(
            owner=self.user, name="Demo Studio", profile="Synthetic product studio", voice="Simple and friendly",
            current="Synthetic facts only", source="Local fixture", valid_until=timezone.localdate()+timedelta(days=30),
        )
        self.run = ContentRun.objects.create(
            workspace=self.company, author=self.user, model="browser-fixture", context=snapshot_company_context(self.company),
            selected=0, ideas=[{"title": "En lugn produktvisning", "angle": "Visa produkten", "photo_brief": "An older product idea"}],
            draft={"photo_brief": "A white product on a table in morning light.", "instagram": "Keep copy.", "facebook": "Keep Facebook copy."},
        )
        self.assets = []
        for index in range(3):
            content = BytesIO()
            Image.new("RGB", (960, 640), (210 + index * 10, 230, 220)).save(content, "PNG")
            self.assets.append(store_asset(self.company, content.getvalue(), alt_text=f"Synthetic product {index+1}"))
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(self.executor.shutdown)
        self.browser_errors = []
        self.observations = {"baseline": BASELINE, "checks": []}
        # Server-side paid entry points must fail even if accidentally reached.
        for entry in ("engine.media.providers.start_video", "engine.media.providers.generate_images", "engine.media.providers.upload_input"):
            self.stack.enter_context(patch(entry, side_effect=AssertionError("Paid/external provider call forbidden")))
        self.stack.enter_context(patch("engine.media.providers.estimate_video", side_effect=self.estimate))

    @staticmethod
    def estimate(job):
        model = job.parameters["provider_model"]
        return model, {"prompt": job.prompt}, {"estimate": {"usd": "0.80"}, "model": model}

    def url(self, name, **kwargs):
        return self.live_server_url + reverse("engine:" + name, kwargs={"workspace_id": self.company.pk, **kwargs})

    def login(self, context):
        context.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).netloc == urlparse(self.live_server_url).netloc else route.abort())
        page = context.new_page()
        self.active_page = page
        page.set_default_timeout(30000)
        page.on("pageerror", lambda error: self.browser_errors.append(str(error)))
        page.on("response", lambda response: self.observations.setdefault("server_errors", []).append({"status": response.status, "path": urlparse(response.url).path}) if response.status >= 500 else None)
        page.goto(self.live_server_url + reverse("login"))
        page.locator("[name=username]").fill("product-flow@example.invalid")
        page.locator("[name=password]").fill("isolated-demo-only")
        page.get_by_role("button", name="Logga in", exact=True).click()
        page.wait_for_url(lambda url: "/accounts/login/" not in str(url))
        return page

    def screenshot(self, page, name):
        page.screenshot(path=str(EVIDENCE / (name + ".png")), full_page=True)

    def test_creation_flow(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = self.login(context)
            try:
                media = self.url("media", run_id=self.run.pk)
                page.goto(media + "?kind=image#generate")
                expect(page.locator("#media-brief")).to_be_visible()
                self.screenshot(page, "desktop-image")
                original = "A white product in morning light. Keep the camera static and let the flag move."
                page.locator("#media-brief").fill(original)
                page.locator(".media-quick-actions a").filter(has_text="Animera").first.click()
                expect(page.locator("#media-brief")).to_be_visible()
                # The response becomes visible before deferred draft restoration finishes.
                page.wait_for_load_state("domcontentloaded")
                if not BASELINE:
                    expect(page.locator("#media-brief")).to_have_value(original)
                preserved = page.locator("#media-brief").input_value() == original
                self.observations["brief_preserved_on_animate"] = preserved
                self.observations["video_brief"] = page.locator("#media-brief").input_value()
                self.screenshot(page, "desktop-video")
                if BASELINE:
                    self.assertFalse(preserved)
                    page.locator(".generation-submit").click()
                    self.observations["review_url"] = page.url
                    self.observations["notices"] = page.locator(".app-notices").inner_text() if page.locator(".app-notices").count() else ""
                    self.assertEqual(self.executor.submit(MediaGeneration.objects.count).result(), 0)
                    page.goto(media + "?kind=video#generate")
                    page.set_viewport_size({"width": 390, "height": 844})
                    self.screenshot(page, "mobile-video")
                    self.observations["checks"].append("baseline_loses_text_and_rejects_own_default")
                    return
                self.assertTrue(preserved)
                source = page.locator("#media-source-asset").input_value()
                self.assertTrue(source)
                end = next(str(asset.pk) for asset in self.assets if str(asset.pk) != source)
                # Native frame selection, preset and automatic compatible model filtering.
                page.locator("#media-end-asset").select_option(end)
                page.locator("#media-preset").select_option("before_after")
                expect(page.locator("#media-brief")).to_have_value(original)
                expect(page.locator('[data-frame-preview="end_asset"]')).to_be_visible()
                model_ids = page.locator("#media-model-override option").evaluate_all("items => items.map(item => item.value)")
                self.assertFalse(any("kling" in model for model in model_ids))
                self.assertIn("bytedance/seedance-2.5", model_ids)
                page.locator("#media-shape").select_option("landscape")
                page.locator(".generation-kind-switch").get_by_role("link", name="Bild", exact=True).click()
                expect(page.locator("#media-brief")).to_have_value(original)
                page.locator(".generation-kind-switch").get_by_role("link", name="Video", exact=True).click()
                expect(page.locator("#media-end-asset")).to_have_value(end)
                expect(page.locator("#media-preset")).to_have_value("before_after")
                expect(page.locator("#media-shape")).to_have_value("landscape")
                page.locator(".media-nav").get_by_role("link", name="Uppladdat", exact=True).click()
                expect(page.locator("#media-brief")).to_have_value(original)
                expect(page.locator("#media-end-asset")).to_have_value(end)
                self.observations["checks"].append("draft_survives_animate_kind_and_filter_navigation")
                # Invalid preset pairing: server re-renders the typed idea; repair in place.
                page.locator("#media-end-asset").select_option("")
                page.locator(".generation-submit").click()
                expect(page.locator(".composer-errors")).to_be_visible()
                expect(page.locator("#media-brief")).to_have_value(original)
                expect(page.locator("#media-source-asset")).to_have_value(source)
                page.locator("#media-end-asset").select_option(end)
                self.observations["checks"].append("invalid_submit_preserves_idea_and_can_be_repaired")
                # Real app review with explicitly synthetic read-only estimate.
                page.locator(".generation-submit").click()
                page.wait_for_url("**/media/jobs/**/")
                self.assertEqual(self.executor.submit(MediaGeneration.objects.count).result(), 1)
                job = self.executor.submit(MediaGeneration.objects.get).result()
                self.assertEqual(job.status, "queued")
                self.assertEqual(job.parameters["creative"]["recipe"]["recipe_id"], "before_after")
                self.assertEqual(job.brief, original)
                self.screenshot(page, "review")
                self.observations["checks"].append("price_review_without_paid_start")
                # Retry restores the reviewed choice rather than a stale tab draft.
                page.goto(media + "?retry=" + str(job.pk) + "#generate")
                expect(page.locator("#media-preset")).to_have_value("before_after")
                expect(page.locator("#media-end-asset")).to_have_value(end)
                # Actual handoff through the existing engines, preserving company/run facts.
                sequence_idea = "Scene 1: show the product. Scene 2: show the place. Scene 3: calm ending."
                page.locator("#media-brief").fill(sequence_idea)
                page.get_by_role("button", name="Forts\u00e4tt i Sequence", exact=True).click()
                page.wait_for_url("**/sequences/?run_id=*")
                expect(page.locator('textarea[name="brief"]')).to_have_value(sequence_idea)
                self.screenshot(page, "sequence-handoff")
                page.goto(media + "?kind=video#generate")
                motion_idea = "A short typographic summary with a calm ending."
                page.locator("#media-brief").fill(motion_idea)
                page.get_by_role("button", name="Forts\u00e4tt i Motion", exact=True).click()
                page.wait_for_url("**/motion/?run_id=*")
                expect(page.locator('[name="body"]')).to_have_value(motion_idea)
                self.screenshot(page, "motion-handoff")
                self.executor.submit(self.run.refresh_from_db).result()
                self.assertEqual(self.run.draft["instagram"], "Keep copy.")
                self.assertEqual(self.run.context["current"], "Synthetic facts only")
                self.observations["checks"].append("sequence_and_motion_reuse_same_run_and_preserve_copy_facts")
                # Responsive layout, real DOM width checks and screenshots.
                page.goto(media + "?kind=video#generate")
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 900})
                    self.screenshot(page, "video-" + str(width))
                    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                    self.observations["overflow_" + str(width)] = overflow
                    self.assertFalse(overflow, f"Horizontal overflow at {width}px")
                self.observations["checks"].append("responsive_320_390_768_1440")
                # Progressive enhancement: native form still works without JavaScript.
                native_context = browser.new_context(java_script_enabled=False)
                native = self.login(native_context)
                native.goto(media + "?kind=video&source=" + source + "&end_source=" + end + "#generate")
                expect(native.locator("#media-source-asset")).to_have_value(source)
                expect(native.locator('[data-frame-preview="end_asset"]')).to_be_visible()
                native.locator("#media-preset").select_option("before_after")
                native.locator("#media-end-asset").select_option("")
                self.screenshot(native, "native-form-before-submit")
                # Exercise the native keyboard submit path with page scripts disabled.
                # This path does not rely on pointer stability polling with disabled page scripts.
                native.bring_to_front()
                expect(native.locator(".generation-submit")).to_be_enabled()
                native.locator(".generation-submit").press("Enter")
                expect(native.locator(".composer-errors")).to_be_visible()
                native_context.close()
                blocked_context = browser.new_context()
                blocked_context.add_init_script("Object.defineProperty(window, 'sessionStorage', {get(){throw new DOMException('Blocked','SecurityError');}})")
                blocked = self.login(blocked_context)
                blocked.goto(media + "?kind=video#generate")
                expect(blocked.locator('[data-composer-status]')).to_contain_text("Webbl\u00e4saren till\u00e5ter inte")
                blocked_context.close()
                self.observations["checks"].append("native_form_and_storage_disabled_fallbacks")
                self.assertEqual(self.browser_errors, [])
                self.assertEqual(self.observations.get("server_errors", []), [])
            except Exception:
                page = self.active_page if not self.active_page.is_closed() else page
                self.screenshot(page, "failure")
                (EVIDENCE / "failure.txt").write_text(traceback.format_exc() + "\nURL: " + page.url + "\n" + page.locator("body").inner_text(), encoding="utf-8")
                raise
            finally:
                self.observations["javascript_errors"] = self.browser_errors
                (EVIDENCE / "observations.json").write_text(json.dumps(self.observations, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps(self.observations, ensure_ascii=True))
                browser.close()


if __name__ == "__main__":
    # In-memory SQLite shares one connection between the live server and test
    # threads, causing random authentication/asset failures under browser load.
    # A temporary file gives each thread its own connection without touching data.
    with tempfile.TemporaryDirectory(prefix="product-flow-db-") as database_dir:
        database = connections["default"]
        database.settings_dict["TEST"]["NAME"] = str(Path(database_dir) / "browser.sqlite3")
        failures = DiscoverRunner(verbosity=1, interactive=False).run_tests(["__main__.ProductFlowBrowserTests"])
    raise SystemExit(bool(failures))
