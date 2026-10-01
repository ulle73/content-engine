"""Isolated real-browser regression suite. No paid providers or production data.

Run: python scripts/product_flow_browser.py
Install test-only browser: pip install playwright==1.55.0 && python -m playwright install chromium
Covers preserved planner behavior, draft recovery and native fallbacks.
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

EVIDENCE = ROOT / "data" / "product-flow-browser" / "combined"
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
        self.addCleanup(self.close_executor)
        self.browser_errors = []
        self.observations = {"checks": []}
        # Server-side paid entry points must fail even if accidentally reached.
        for entry in ("engine.media.providers.start_video", "engine.media.providers.generate_images", "engine.media.providers.upload_input"):
            self.stack.enter_context(patch(entry, side_effect=AssertionError("Paid/external provider call forbidden")))
        self.stack.enter_context(patch("engine.media.providers.estimate_video", side_effect=self.estimate))

    @staticmethod
    def estimate(job):
        model = job.parameters["provider_model"]
        return model, {"prompt": job.prompt}, {"estimate": {"usd": "0.80"}, "model": model}

    def close_executor(self):
        # ORM connections belong to the worker thread; close them there before
        # Django deletes the temporary SQLite file on Windows.
        self.executor.submit(connections.close_all).result()
        self.executor.shutdown()

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

    def select_frame(self, page, role, asset_id):
        page.locator(f'[data-open-frame="{role}"]').click()
        page.locator(f'#creator-reference-grid [data-asset-id="{asset_id}"]').click()
        expect(page.locator("#creator-reference-picker")).to_be_hidden()

    def test_creation_flow(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = self.login(context)
            try:
                media = self.url("media", run_id=self.run.pk)
                page.goto(media)
                form = page.locator("#creator-form")
                expect(form.locator('[name="brief"]')).to_be_visible()
                expect(form.locator('[name="brief"]')).to_have_value(self.run.draft["photo_brief"])
                self.screenshot(page, "desktop-image")
                original = "Static camera on a white product in morning light. Let the flag move."
                form.locator('[name="brief"]').fill(original)
                page.locator('.media-library-section > summary').click()
                page.locator(".media-quick-actions a").filter(has_text="Animera").first.click()
                expect(form.locator('[name="brief"]')).to_have_value(original)
                source = form.locator('[name="source_asset"]').input_value()
                self.assertTrue(source)
                end = next(str(asset.pk) for asset in self.assets if str(asset.pk) != source)
                self.select_frame(page, "end_asset", end)
                form.locator('[name="recipe_id"]').select_option("before_after")
                form.locator('[name="duration_seconds"]').select_option("8")
                form.locator('[name="shape"]').select_option("landscape")
                form.locator('details.creator-options').first.locator('summary').click()
                form.locator('[name="camera"]').select_option("static")
                expect(page.locator('#creator-plan-status')).to_contain_text('8 sekunder')
                prompt = page.locator('#creator-compiled-prompt').text_content()
                camera_line = next(line for line in prompt.splitlines() if line.startswith('CAMERA:'))
                self.assertIn('static', camera_line)
                self.assertNotIn('push', camera_line.lower())
                self.assertNotIn('orbit', camera_line.lower())
                form.locator('nav a[href="?kind=image#generate"]').click()
                expect(form.locator('[name="brief"]')).to_have_value(original)
                # Video-specific controls must not leak into image planning.
                expect(page.locator('#creator-plan-status')).to_contain_text('Auto rekommenderar')
                form.locator('nav a[href="?kind=video#generate"]').click()
                expect(form.locator('[name="end_asset"]')).to_have_value(end)
                expect(form.locator('[name="recipe_id"]')).to_have_value("before_after")
                expect(form.locator('[name="duration_seconds"]')).to_have_value("8")
                expect(form.locator('[name="camera"]')).to_have_value("static")
                expect(form.locator('[name="shape"]')).to_have_value("landscape")
                page.locator('.media-library-section > summary').click()
                page.locator(".media-nav").get_by_role("link", name="Uppladdat", exact=True).click()
                expect(form.locator('[name="brief"]')).to_have_value(original)
                expect(form.locator('[name="end_asset"]')).to_have_value(end)
                self.observations["checks"].append("draft_survives_animate_kind_and_filter_navigation")
                # Remove and repair a required frame through the actual picker UI.
                page.locator('[data-remove-frame="end_asset"]').click()
                page.locator('#creator-submit').click()
                expect(page.locator('.creator-errors')).to_be_visible()
                expect(form.locator('[name="brief"]')).to_have_value(original)
                expect(form.locator('[name="source_asset"]')).to_have_value(source)
                self.select_frame(page, "end_asset", end)
                page.locator('#creator-submit').click()
                page.wait_for_url("**/media/jobs/**/")
                job = self.executor.submit(MediaGeneration.objects.get).result()
                self.assertEqual(job.status, 'queued')
                self.assertEqual(job.brief, original)
                self.assertEqual(job.parameters['creative']['recipe']['recipe_id'], 'before_after')
                self.assertTrue(job.usage.get('reviewed_at'))
                self.screenshot(page, "review")
                page.goto(media + '?retry=' + str(job.pk) + '#generate')
                expect(form.locator('[name="recipe_id"]')).to_have_value('before_after')
                expect(form.locator('[name="end_asset"]')).to_have_value(end)
                self.observations["checks"].append("invalid_repair_and_synthetic_price_review_retry_without_paid_start")
                # Draft lifetime, identity scoping, and no tokens in stored fields.
                state = page.evaluate("""() => {
                    const form = document.getElementById('creator-form');
                    const key = 'ce:creator:v2:' + form.dataset.stateKey;
                    return {key, value: JSON.parse(sessionStorage.getItem(key))};
                }""")
                self.assertIn(str(self.user.pk) + ':' + str(self.company.pk) + ':' + str(self.run.pk), state['key'])
                stored = state['value']['shared'] | state['value']['kinds']['video']
                self.assertFalse({'token', 'csrfmiddlewaretoken', 'provider_id'} & set(stored))
                context.add_init_script("""if (sessionStorage.getItem('test-expire-draft') === '1') {
                    Object.keys(sessionStorage).filter(key => key.startsWith('ce:creator:v2:')).forEach(key => {
                        const state = JSON.parse(sessionStorage.getItem(key));
                        state.savedAt = Date.now() - 3 * 60 * 60 * 1000;
                        sessionStorage.setItem(key, JSON.stringify(state));
                    });
                    sessionStorage.removeItem('test-expire-draft');
                }""")
                page.evaluate("sessionStorage.setItem('test-expire-draft', '1')")
                page.goto(media + '?kind=video#generate')
                expect(form.locator('[name="brief"]')).to_have_value(self.run.draft['photo_brief'])
                expect(form.locator('[name="end_asset"]')).to_have_value('')
                self.observations['checks'].append('two_hour_expiry_scoped_storage_without_tokens')
                sequence_idea = 'Scene 1: show the product. Scene 2: show the place. Scene 3: calm ending.'
                form.locator('[name="brief"]').fill(sequence_idea)
                self.select_frame(page, 'source_asset', source)
                self.select_frame(page, 'end_asset', end)
                form.locator('button[name="workflow"][value="sequence"]').click()
                expect(page.locator('textarea[name="brief"]')).to_have_value(sequence_idea)
                expect(page.locator('input[name="image_ids"]')).to_have_count(2)
                self.screenshot(page, 'sequence-handoff')
                page.goto(media + '?kind=video#generate')
                # A saved server change invalidates an older browser baseline.
                expect(form.locator('[name="brief"]')).to_have_value(sequence_idea)
                motion_idea = 'A short typographic summary with a calm ending.'
                form.locator('[name="brief"]').fill(motion_idea)
                form.locator('button[name="workflow"][value="motion"]').click()
                expect(page.locator('[name="body"]')).to_have_value(motion_idea)
                self.executor.submit(self.run.refresh_from_db).result()
                self.assertEqual(self.run.draft['instagram'], 'Keep copy.')
                self.assertEqual(self.run.context['current'], 'Synthetic facts only')
                self.observations['checks'].append('ordered_frames_and_intent_handoff_preserves_copy_and_facts')
                page.goto(media + '?kind=video#generate')
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({'width': width, 'height': 900})
                    self.screenshot(page, 'video-' + str(width))
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Overflow at {width}')
                self.observations['checks'].append('responsive_320_390_768_1440')
                native_context = browser.new_context(java_script_enabled=False)
                native = self.login(native_context)
                native.goto(media + '?kind=video&source=' + source + '&end_source=' + end + '#generate')
                expect(native.locator('[name="source_asset"]')).to_have_value(source)
                native.locator('[name="recipe_id"]').select_option('before_after')
                native.locator('[name="end_asset"]').select_option('')
                native.locator('#creator-submit').press('Enter')
                expect(native.locator('.creator-errors')).to_be_visible()
                native_context.close()
                blocked_context = browser.new_context()
                blocked_context.add_init_script("Object.defineProperty(window, 'sessionStorage', {get(){throw new DOMException('Blocked','SecurityError');}})")
                blocked = self.login(blocked_context)
                blocked.goto(media + '?kind=video#generate')
                expect(blocked.locator('#creator-storage-status')).to_contain_text('Webbläsaren tillåter inte')
                blocked_context.close()
                self.observations['checks'].append('native_form_and_blocked_storage_fallback')
                page.set_viewport_size({'width': 1440, 'height': 1000})
                # Logout must remove all creator drafts and avoid saving again on pagehide.
                page.goto(self.url('sequence_list'))
                page.locator('form[action$="/accounts/logout/"] button').locator("visible=true").first.click()
                page.wait_for_url(lambda url: '/accounts/login/' in str(url))
                remaining = page.evaluate("Object.keys(sessionStorage).filter(key => key.startsWith('ce:creator:'))")
                self.assertEqual(remaining, [])
                self.observations['checks'].append('logout_clears_drafts')
                self.assertEqual(self.browser_errors, [])
                self.assertEqual(self.observations.get('server_errors', []), [])
            except Exception:
                page = self.active_page if not self.active_page.is_closed() else page
                self.screenshot(page, 'failure')
                (EVIDENCE / 'failure.txt').write_text(traceback.format_exc() + '\nURL: ' + page.url + '\n' + page.locator('body').inner_text(), encoding='utf-8')
                raise
            finally:
                self.observations['javascript_errors'] = self.browser_errors
                (EVIDENCE / 'observations.json').write_text(json.dumps(self.observations, ensure_ascii=False, indent=2), encoding='utf-8')
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
