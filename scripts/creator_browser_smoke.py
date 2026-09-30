"""Real-browser acceptance with synthetic data and no provider credentials.

Run with Python + Playwright Chromium installed. Never uses production settings,
a database URL, cloud media, a real company or paid generation. Evidence is saved
under data/creator-browser; --baseline only inspects the starting product.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ORIGIN = "http://127.0.0.1:8765"


def serve():
    os.environ["DJANGO_SETTINGS_MODULE"] = "engine.test_settings"
    os.environ["SECRET_KEY"] = "isolated-creator-browser-only"
    os.environ["APP_URL"] = ORIGIN
    os.environ["MEDIA_STORAGE"] = "local"
    import engine.test_settings as config
    target = Path(os.environ["CREATOR_TEST_ROOT"])
    config.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(target / "ui.sqlite3")}}
    config.MEDIA_ROOT = target / "media"
    import django
    django.setup()
    from datetime import date
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django.urls import reverse
    from PIL import Image, ImageDraw
    from engine.forms import snapshot_company_context
    from engine.media import store_asset
    from engine.models import Company, ContentRun
    call_command("migrate", interactive=False, verbosity=0)
    user = get_user_model().objects.create_user(username="creator@example.test", password="Isolated-test-only-2026!")
    company = Company.objects.create(owner=user, name="Golfkuponger TEST", profile="Syntetiskt underlag. Golfpresentkort.", voice="Varm och enkel svenska.", current="Endast testdata, inga verkliga kampanjresultat.", source="Isolerad testfixture", valid_until=date(2099, 1, 1))
    run = ContentRun.objects.create(workspace=company, author=user, model="creative-studio", context={**snapshot_company_context(company), "media_only": True}, ideas=[{"title": "Min testvideo", "photo_brief": "", "angle": ""}], selected=0, draft={"photo_brief": "", "instagram": "", "facebook": ""})
    assets = []
    for label, radius in [("Startbild TEST", 80), ("Slutbild TEST", 160)]:
        image = Image.new("RGB", (720, 1280), "#204b3d")
        draw = ImageDraw.Draw(image)
        draw.ellipse((360-radius, 700-radius, 360+radius, 700+radius), fill="white")
        draw.text((25, 25), label, fill="white")
        blob = io.BytesIO()
        image.save(blob, "PNG")
        asset = store_asset(company, blob.getvalue(), alt_text=label)
        assets.append(str(asset.pk))
    fixture = {"company": str(company.pk), "run": str(run.pk), "assets": assets, "media": reverse("engine:media", kwargs={"workspace_id": company.pk, "run_id": run.pk}), "library": reverse("engine:media_library", kwargs={"workspace_id": company.pk})}
    (target / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
    call_command("runserver", "127.0.0.1:8765", use_reloader=False, verbosity=0)


def run_browser(baseline=False):
    from playwright.sync_api import sync_playwright
    evidence = ROOT / "data" / "creator-browser"
    evidence.mkdir(parents=True, exist_ok=True)
    # Fail rather than accidentally reuse an application's configured secrets.
    forbidden = ("DATABASE_URL", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "HIGGSFIELD_API_KEY_GK", "HIGGSFIELD_API_KEY", "R2_ACCESS_KEY_ID", "RENDER_EXTERNAL_URL")
    if any(os.environ.get(key) for key in forbidden):
        raise RuntimeError("Use a clean test environment without application/provider configuration.")
    with tempfile.TemporaryDirectory(prefix="creator-browser-") as temporary:
        env = {**os.environ, "CREATOR_TEST_ROOT": temporary}
        with (evidence / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, __file__, "--server"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(90):
                    if server.poll() is not None:
                        raise RuntimeError("Isolated server exited; see server.log")
                    try:
                        with urlopen(ORIGIN + "/accounts/login/", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(0.5)
                else:
                    raise RuntimeError("Isolated server did not become ready")
                fixture = json.loads((Path(temporary) / "fixture.json").read_text())
                checks = []
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(ORIGIN + "/accounts/login/")
                    page.locator('input[name="username"]').fill("creator@example.test")
                    page.locator('input[name="password"]').fill("Isolated-test-only-2026!")
                    page.locator('button[type="submit"]').click()
                    page.wait_for_url(lambda url: "/accounts/login/" not in url)
                    paths = {"library": fixture["library"], "creator": fixture["media"] + "?kind=video&source=" + fixture["assets"][0] + "&end_source=" + fixture["assets"][1] + "#generate"}
                    for width in (390, 1440):
                        page.set_viewport_size({"width": width, "height": 1000})
                        for name, path in paths.items():
                            response = page.goto(ORIGIN + path)
                            assert response and response.status == 200, (name, response.status if response else None)
                            overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                            page.screenshot(path=str(evidence / f"{'before' if baseline else 'after'}-{name}-{width}.png"), full_page=True)
                            checks.append({"page": name, "width": width, "http": response.status, "overflow": overflow})
                            assert not overflow, (name, width, "horizontal overflow")
                    assert not errors, errors
                    (evidence / "acceptance.json").write_text(json.dumps({"baseline": baseline, "checks": checks, "page_errors": errors}, indent=2), encoding="utf-8")
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    serve() if args.server else run_browser(args.baseline)
