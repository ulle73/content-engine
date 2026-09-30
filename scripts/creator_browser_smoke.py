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
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
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
    fixture["pages"] = {name: reverse("engine:" + name, kwargs={"workspace_id": company.pk}) for name in (
        "home", "media_library", "sequence_list", "motion_list", "prompt_library",
        "intelligence", "market_intelligence", "own_performance", "settings", "costs")}
    fixture["review"] = reverse("engine:review", kwargs={"workspace_id": company.pk, "run_id": run.pk})
    # More than one picker page; every entry is real media in isolated local storage.
    for index in range(61):
        store_asset(company, blob.getvalue(), alt_text=f"Biblioteksbild TEST {index}")
    (target / "upload.png").write_bytes(blob.getvalue())
    (target / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
    call_command("runserver", "127.0.0.1:8765", use_reloader=False, verbosity=0)


def exercise_creator(page, fixture, target, evidence, checks):
    from playwright.sync_api import expect
    intent = "Kameran n\u00e4rmar sig golfbollen. Bollen lyfter."
    page.goto(ORIGIN + fixture["media"] + "?kind=video#generate")
    form = page.locator("#creator-form")
    expect(form.locator('[name="brief"]')).to_have_value("")
    form.locator('[name="brief"]').fill(intent)
    # In-place picker, multiple pages and search preserve an already typed idea.
    page.locator('[data-open-frame="source_asset"]').click()
    expect(page.locator("#creator-reference-grid button")).to_have_count(60)
    page.locator("#creator-more").click()
    expect(page.locator("#creator-reference-grid button")).to_have_count(63)
    page.locator("#creator-search").fill("Startbild TEST")
    page.locator(f'[data-asset-id="{fixture["assets"][0]}"]').click()
    page.locator('[data-open-frame="end_asset"]').click()
    page.locator("#creator-search").fill("Slutbild TEST")
    page.locator(f'[data-asset-id="{fixture["assets"][1]}"]').click()
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    form.locator('[name="duration_seconds"]').select_option("8")
    form.locator('[name="recipe_id"]').select_option("premium_product_reveal")
    form.locator("details.creator-options").first.locator("summary").click()
    form.locator('[name="camera"]').select_option("push_in")
    form.locator('[name="ending"]').select_option("match_end")
    expect(page.locator("#creator-plan-status")).to_contain_text("Seedance 2.5")
    expect(page.locator("#creator-plan-status")).to_contain_text("8 sekunder")
    expect(page.locator("#creator-prompt-details")).to_be_visible()
    assert "END FRAME:" in page.locator("#creator-compiled-prompt").text_content()
    page.locator("#creator-swap").click()
    expect(form.locator('[name="source_asset"]')).to_have_value(fixture["assets"][1])
    expect(form.locator('[name="end_asset"]')).to_have_value(fixture["assets"][0])
    page.locator("#creator-swap").click()
    # Invalid old choices are not silently dropped when requirements change.
    form.locator("details.creator-options").nth(1).locator("summary").click()
    kling = form.locator('[name="model_override"] option[value="kling-video/v2.5-turbo/pro"]')
    assert kling.evaluate("o => o.hidden && o.disabled"), "Kling must not offer end frames"
    form.locator('[name="model_override"]').select_option("bytedance/seedance-2.0")
    expect(page.locator("#creator-plan-status")).to_contain_text("Vald modell: Seedance 2.0")
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    form.locator('[name="model_override"]').select_option("")
    # Reload and type switches keep intent, frames and supported choices.
    page.reload()
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    expect(form.locator('[name="source_asset"]')).to_have_value(fixture["assets"][0])
    expect(form.locator('[name="end_asset"]')).to_have_value(fixture["assets"][1])
    expect(form.locator('[name="duration_seconds"]')).to_have_value("8")
    form.locator('nav a[href="?kind=image#generate"]').click()
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    form.locator('nav a[href="?kind=video#generate"]').click()
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    expect(form.locator('[name="end_asset"]')).to_have_value(fixture["assets"][1])
    # Browser upload uses real multipart -> MediaAsset -> compiler, no navigation.
    page.locator('[data-open-frame="source_asset"]').click()
    page.locator("#creator-upload").set_input_files(str(target / "upload.png"))
    expect(page.locator("#creator-reference-picker")).to_be_hidden()
    uploaded = form.locator('[name="source_asset"]').input_value()
    assert uploaded and uploaded not in fixture["assets"]
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    page.locator('[data-open-frame="source_asset"]').click()
    page.locator("#creator-search").fill("Startbild TEST")
    page.locator(f'[data-asset-id="{fixture["assets"][0]}"]').click()
    # Local preview has not created a paid-provider job or started a network call.
    expect(page.locator("#creator-plan-status")).to_contain_text("8 sekunder")
    with sqlite3.connect(target / "ui.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM engine_mediageneration").fetchone()[0] == 0
    page.screenshot(path=str(evidence / "after-creator-interaction.png"), full_page=True)
    page.locator("#creator-submit").click()
    page.wait_for_url(re.compile(r"/media/jobs/[^/]+/$"))
    job_url = page.url
    expect(page.get_by_role("heading", name="Granska f\u00f6re start", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Starta betald generation", exact=True)).to_have_count(0)
    expect(page.locator(".generation-reference-review img")).to_have_count(2)
    page.screenshot(path=str(evidence / "after-review-desktop.png"), full_page=True)
    page.get_by_role("button", name="Avbryt", exact=True).click()
    if "/media/jobs/" not in page.url:
        page.goto(job_url)
    page.locator('a[href*="?retry="]').click()
    expect(form.locator('[name="brief"]')).to_have_value(intent)
    expect(form.locator('[name="duration_seconds"]')).to_have_value("8")
    expect(form.locator('[name="recipe_id"]')).to_have_value("premium_product_reveal")
    expect(form.locator('[name="end_asset"]')).to_have_value(fixture["assets"][1])
    # Handoff does not need an AI model or a copy/paste operation.
    form.locator('button[name="workflow"][value="sequence"]').click()
    expect(page.locator("#sequence-brief")).to_have_value(intent)
    expect(page.locator('input[name="image_ids"]')).to_have_count(2)
    page.locator(".sequence-create-form button[type=submit]").click()
    page.wait_for_url(re.compile(r"/sequences/[^/]+/$"))
    fixture["pages"]["sequence_workspace"] = page.url.removeprefix(ORIGIN)
    with sqlite3.connect(target / "ui.sqlite3") as db:
        rows = db.execute("SELECT asset_id FROM engine_sequenceanchor ORDER BY position").fetchall()
        assert [row[0].replace("-", "") for row in rows] == [value.replace("-", "") for value in fixture["assets"]]
    # The known numbers are filled, but an unknown area is never invented.
    page.goto(ORIGIN + fixture["media"] + "?kind=video#generate")
    form.locator('[name="brief"]').fill("September wrapped: 877 inl\u00f6sen och 721515 kr.")
    form.locator('button[name="workflow"][value="motion"]').click()
    expect(page.locator("#motion-template")).to_have_value("monthly-wrapped")
    expect(page.locator("#id_month")).to_have_value("September")
    expect(page.locator("#id_count")).to_have_value("877")
    expect(page.locator("#id_total")).to_have_value("721515.0")
    expect(page.locator("#id_area")).to_have_value("")
    page.locator("#id_area").fill("TESTOMRADE - syntetiskt")
    page.locator(".motion-form button[type=submit]").click()
    page.wait_for_url(re.compile(r"/motion/[^/]+/$"))
    fixture["pages"]["motion_workspace"] = page.url.removeprefix(ORIGIN)
    with sqlite3.connect(target / "ui.sqlite3") as db:
        jobs = db.execute("SELECT status, provider_id FROM engine_mediageneration").fetchall()
        assert len(jobs) == 1 and jobs[0][0] == "canceled" and not jobs[0][1], jobs
    checks.append({"flow": "frames-search-pagination-upload-model-recompile-reload-retry-sequence-motion", "passed": True, "paid_provider_starts": 0})


def run_browser(baseline=False):
    from playwright.sync_api import sync_playwright
    evidence = ROOT / "data" / "creator-browser"
    evidence.mkdir(parents=True, exist_ok=True)
    forbidden = ("DATABASE_URL", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "HIGGSFIELD_API_KEY_GK", "HIGGSFIELD_API_KEY", "R2_ACCESS_KEY_ID", "RENDER_EXTERNAL_URL", "MOTION_WORKER_TOKEN", "MOTION_WORKER_URL")
    if any(os.environ.get(key) for key in forbidden):
        raise RuntimeError("Use a clean test environment without application/provider configuration.")
    with tempfile.TemporaryDirectory(prefix="creator-browser-") as temporary:
        target = Path(temporary)
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
                fixture = json.loads((target / "fixture.json").read_text())
                checks, errors = [], []
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    context = browser.new_context(viewport={"width": 1440, "height": 1000})
                    context.tracing.start(screenshots=True, snapshots=True, sources=True)
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    try:
                        page.goto(ORIGIN + "/accounts/login/")
                        page.locator('input[name="username"]').fill("creator@example.test")
                        page.locator('input[name="password"]').fill("Isolated-test-only-2026!")
                        page.locator('button[type="submit"]').click()
                        page.wait_for_url(lambda url: "/accounts/login/" not in url)
                        if not baseline:
                            exercise_creator(page, fixture, target, evidence, checks)
                        paths = {**fixture["pages"], "creator": fixture["media"] + "?kind=video&source=" + fixture["assets"][0] + "&end_source=" + fixture["assets"][1] + "#generate", "review": fixture["review"]}
                        for width in (320, 390, 767, 1440):
                            page.set_viewport_size({"width": width, "height": 1000})
                            for name, path in paths.items():
                                response = page.goto(ORIGIN + path)
                                assert response and response.status == 200, (name, response.status if response else None)
                                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                                page.screenshot(path=str(evidence / f"{'before' if baseline else 'after'}-{name}-{width}.png"), full_page=True)
                                checks.append({"page": name, "width": width, "http": response.status, "overflow": overflow})
                                assert not overflow, (name, width, "horizontal overflow")
                        assert not errors, errors
                    except Exception as exc:
                        checks.append({"failure": str(exc), "url": page.url})
                        page.screenshot(path=str(evidence / "failure.png"), full_page=True)
                        raise
                    finally:
                        (evidence / "acceptance.json").write_text(json.dumps({"baseline": baseline, "checks": checks, "page_errors": errors}, indent=2), encoding="utf-8")
                        context.tracing.stop(path=str(evidence / "trace.zip"))
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
