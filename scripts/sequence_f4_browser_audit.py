#!/usr/bin/env python3
import argparse
import io
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")

import django

django.setup()

from PIL import Image
from django.contrib.auth import get_user_model

from engine.media import store_asset
from engine.models import Company, ContentRun, MediaGeneration, SequenceClipVersion
from engine.sequence import (
    add_anchor,
    create_clip,
    create_sequence_project,
    prepare_anchor_chain_version,
    select_clip_version,
)

AUDIT_FILE = Path(".f4-audit.json")
ARTIFACT_DIR = Path("artifacts/sequence-f4")


def picture(rgb):
    out = io.BytesIO()
    Image.new("RGB", (960, 540), rgb).save(out, "PNG")
    return out.getvalue()


def seed():
    username = "sequence-f4-audit@example.test"
    password = "F4-audit-only-2026!"
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save(update_fields=["password"])

    company, _ = Company.objects.get_or_create(
        owner=user,
        defaults={
            "name": "Golfkuponger F4 audit",
            "profile": "Premium golf value service",
            "voice": "Warm and premium",
            "current": "Sequence F4 browser audit",
            "source": "CI fixture",
        },
    )
    project = create_sequence_project(
        company,
        author=user,
        title="Premium Golfkuponger sequence with deliberately long responsive title",
        brief="A continuous premium golf story used only for responsive and accessibility verification.",
        format="scroll_story",
        platform="web",
    )
    k0 = add_anchor(
        project,
        store_asset(company, picture((15, 62, 38))),
        position=0,
        label="Opening premium golf landscape anchor",
        locked=False,
    )
    k1 = add_anchor(
        project,
        store_asset(company, picture((35, 102, 66))),
        position=1,
        label="Closing product and landscape anchor",
        locked=True,
    )
    clip = create_clip(
        project,
        k0,
        k1,
        position=0,
        recipe_id="scroll_transition_bridge",
        label="Long continuous hero move without cuts",
    )

    v1 = prepare_anchor_chain_version(clip, brief="Slow premium continuous camera move", token=uuid.uuid4())
    MediaGeneration.objects.filter(pk=v1.generation_id).update(status="completed")
    SequenceClipVersion.objects.filter(pk=v1.pk).update(status="ready")
    v1.refresh_from_db()
    select_clip_version(clip, v1)

    v2 = prepare_anchor_chain_version(clip, brief="Second candidate with a slower camera move", token=uuid.uuid4())
    MediaGeneration.objects.filter(pk=v2.generation_id).update(status="running")
    SequenceClipVersion.objects.filter(pk=v2.pk).update(status="generating")

    v3 = prepare_anchor_chain_version(clip, brief="Third queued review candidate", token=uuid.uuid4())
    MediaGeneration.objects.filter(pk=v3.generation_id).update(status="queued")
    SequenceClipVersion.objects.filter(pk=v3.pk).update(status="review")

    run = ContentRun.objects.create(
        workspace=company,
        author=user,
        context={"media_only": True, "profile": company.profile, "voice": company.voice, "current": company.current},
        ideas=[{"title": "F4 AI Studio smoke", "photo_brief": ""}],
        selected=0,
        draft={"photo_brief": "", "instagram": "", "facebook": ""},
        model="creative-studio",
    )

    payload = {
        "username": username,
        "password": password,
        "sequence_path": f"/company/{company.pk}/sequences/{project.pk}/",
        "media_path": f"/company/{company.pk}/runs/{run.pk}/media/?kind=image#generate",
    }
    AUDIT_FILE.write_text(json.dumps(payload), encoding="utf-8")
    print(json.dumps(payload))


def _assert_page_no_horizontal_overflow(page, label):
    metrics = page.evaluate(
        """() => ({
          htmlScroll: document.documentElement.scrollWidth,
          htmlClient: document.documentElement.clientWidth,
          bodyScroll: document.body.scrollWidth,
          bodyClient: document.body.clientWidth
        })"""
    )
    assert metrics["htmlScroll"] <= metrics["htmlClient"] + 2, f"{label}: html horizontal overflow {metrics}"
    assert metrics["bodyScroll"] <= metrics["bodyClient"] + 2, f"{label}: body horizontal overflow {metrics}"


def _assert_keyboard_focus_visible(page):
    page.locator("body").click(position={"x": 4, "y": 4})
    found = None
    for _ in range(100):
        page.keyboard.press("Tab")
        info = page.evaluate(
            """() => {
              const el = document.activeElement;
              if (!el) return null;
              const inSequence = !!el.closest('.sequence-workspace-page');
              const s = getComputedStyle(el);
              return {
                inSequence,
                tag: el.tagName,
                text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 120),
                outlineStyle: s.outlineStyle,
                outlineWidth: parseFloat(s.outlineWidth || '0'),
                outlineColor: s.outlineColor
              };
            }"""
        )
        if info and info["inSequence"] and info["tag"] in {"A", "BUTTON", "SUMMARY"}:
            if info["outlineStyle"] != "none" and info["outlineWidth"] >= 2:
                found = info
                break
    assert found, "No clearly visible keyboard focus indicator found in Sequence workspace"
    print("keyboard_focus", json.dumps(found))


def _assert_mobile_targets(page):
    selector = ".sequence-workspace-page button, .sequence-workspace-page summary, .sequence-workspace-page .button"
    locator = page.locator(selector)
    checked = 0
    for index in range(locator.count()):
        node = locator.nth(index)
        if not node.is_visible():
            continue
        box = node.bounding_box()
        if not box:
            continue
        checked += 1
        assert box["height"] >= 43.5, f"Mobile target below 44px: {node.evaluate('(el) => el.outerHTML')} => {box}"
    assert checked >= 6, f"Expected multiple mobile targets, checked {checked}"


def audit():
    from playwright.sync_api import sync_playwright

    data = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    base = os.environ.get("F4_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})

        page.goto(base + data["sequence_path"], wait_until="networkidle")
        if page.locator("input[name='username']").count():
            page.locator("input[name='username']").fill(data["username"])
            page.locator("input[name='password']").fill(data["password"])
            page.get_by_role("button", name="Logga in").click()
            page.wait_for_load_state("networkidle")

        assert page.locator(".sequence-workspace-page").count() == 1
        assert page.get_by_role("heading", name="Generera, jämför och välj clip").count() == 1
        assert page.locator("button[aria-label^='Avbryt clip']").count() == 2
        assert page.locator(".sequence-version-card").count() == 3
        _assert_page_no_horizontal_overflow(page, "desktop")
        _assert_keyboard_focus_visible(page)
        page.screenshot(path=str(ARTIFACT_DIR / "desktop-1440.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="networkidle")
        _assert_page_no_horizontal_overflow(page, "mobile")

        status = page.locator(".sequence-status-table")
        assert status.count() == 1
        status_metrics = status.evaluate(
            """el => ({scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, overflowX: getComputedStyle(el).overflowX})"""
        )
        assert status_metrics["scrollWidth"] <= status_metrics["clientWidth"] + 2, f"Mobile status table still scrolls: {status_metrics}"

        anchor = page.locator(".sequence-anchor-node").first
        actions = page.locator(".sequence-anchor-actions").first
        anchor_box = anchor.bounding_box()
        actions_box = actions.bounding_box()
        assert anchor_box and actions_box
        assert actions_box["width"] >= anchor_box["width"] * 0.8, (anchor_box, actions_box)
        assert actions_box["x"] >= anchor_box["x"] - 1
        assert actions_box["x"] + actions_box["width"] <= anchor_box["x"] + anchor_box["width"] + 1

        _assert_mobile_targets(page)
        page.screenshot(path=str(ARTIFACT_DIR / "mobile-390.png"), full_page=True)

        page.goto(base + data["media_path"], wait_until="networkidle")
        assert page.locator(".premium-generation-card").count() == 1
        assert page.locator("#media-brief").count() == 1
        assert page.get_by_text("AI-studio", exact=True).count() >= 1
        _assert_page_no_horizontal_overflow(page, "AI Studio mobile")
        print("ai_studio_smoke ok")

        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if args.seed:
        seed()
    if args.audit:
        audit()
