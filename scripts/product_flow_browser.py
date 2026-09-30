"""Real Chromium smoke test against isolated Django; never calls paid providers."""
import json
import os
import sys
import tempfile
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'engine.test_settings'
import django
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.test.runner import DiscoverRunner
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from playwright.sync_api import sync_playwright
from engine.forms import snapshot_company_context
from engine.media import store_asset
from engine.models import Company, ContentRun

EVIDENCE = ROOT / 'data' / 'product-flow-browser'
EVIDENCE.mkdir(parents=True, exist_ok=True)


class ProductFlowBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.settings_override = override_settings(MEDIA_STORAGE='local', MEDIA_ROOT=self.storage.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = get_user_model().objects.create_user(
            username='product-flow-demo', email='product-flow@example.invalid', password='isolated-demo-only'
        )
        self.company = Company.objects.create(
            owner=self.user, name='Demo Studio', profile='Synthetic product company.',
            voice='Simple and friendly.', current='Synthetic facts only.', source='Local test fixture',
            valid_until=timezone.localdate() + timedelta(days=30),
        )
        self.run = ContentRun.objects.create(
            workspace=self.company, author=self.user, model='browser-fixture',
            context=snapshot_company_context(self.company), selected=0,
            ideas=[{'title': 'En lugn produktvisning', 'angle': 'Visa produkten.', 'photo_brief': 'A white product on a table in morning light.'}],
            draft={'photo_brief': 'A white product on a table in morning light.', 'instagram': 'Synthetic copy.', 'facebook': 'Synthetic copy.'},
        )
        self.assets = []
        for index in range(3):
            image = Image.new('RGB', (960, 640), (210 + index * 10, 230, 220))
            content = BytesIO()
            image.save(content, 'PNG')
            self.assets.append(store_asset(self.company, content.getvalue(), alt_text=f'Synthetic product {index + 1}'))

    def url(self, name, **kwargs):
        return self.live_server_url + reverse('engine:' + name, kwargs={'workspace_id': self.company.pk, **kwargs})

    def test_creation_flow(self):
        observations = {}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(self.live_server_url) else route.abort())
            page = context.new_page()
            page.goto(self.live_server_url + reverse('login'))
            page.locator('[name=username]').fill('product-flow@example.invalid')
            page.locator('[name=password]').fill('isolated-demo-only')
            page.get_by_role('button', name='Logga in', exact=True).click()
            media = self.url('media', run_id=self.run.pk)
            page.goto(media + '?kind=image#generate')
            page.screenshot(path=str(EVIDENCE / 'desktop.png'), full_page=True)
            original = 'My carefully typed product idea must survive selecting an image.'
            page.locator('#media-brief').fill(original)
            page.locator('.media-quick-actions a').filter(has_text='Animera').first.click()
            observations['brief_preserved_on_animate'] = page.locator('#media-brief').input_value() == original
            observations['video_brief'] = page.locator('#media-brief').input_value()
            with patch('engine.media_providers.estimate_video', side_effect=AssertionError('No provider estimate allowed in baseline')):
                page.locator('.generation-submit').click()
                observations['review_url'] = page.url
                observations['notices'] = page.locator('.app-notices').inner_text() if page.locator('.app-notices').count() else ''
            page.goto(media + '?kind=video#generate')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(EVIDENCE / 'mobile.png'), full_page=True)
            observations['mobile_overflow'] = page.evaluate('document.documentElement.scrollWidth > innerWidth')
            (EVIDENCE / 'observations.json').write_text(json.dumps(observations, ensure_ascii=False, indent=2))
            print(json.dumps(observations, ensure_ascii=True))
            browser.close()


if __name__ == '__main__':
    raise SystemExit(bool(DiscoverRunner(verbosity=2, interactive=False).run_tests(['__main__.ProductFlowBrowserTests'])))
