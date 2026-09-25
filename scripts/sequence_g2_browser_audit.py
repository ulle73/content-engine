#!/usr/bin/env python3
import argparse
import io
import json
import os
import sys
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
from engine.models import Company, MediaGeneration, SequenceProject
from engine.sequence import (
    create_clip,
    create_sequence_project,
    materialize_planned_anchor_asset,
)


AUDIT_FILE = Path(".g2-audit.json")
ARTIFACT_DIR = Path("artifacts/sequence-g2")


def picture(rgb):
    out = io.BytesIO()
    Image.new("RGB", (128, 88), rgb).save(out, "PNG")
    return out.getvalue()


def plan():
    return {
        "planner_id": "sequence_planner",
        "planner_version": "1.1.0",
        "status": "final",
        "revision": 1,
        "source_brief": "Premium 2-scene Golfkuponger scroll story",
        "goal": "Visa en sammanhängande premiumresa",
        "format": "scroll_story",
        "platform": "web",
        "scene_count": 2,
        "summary": "Två premiumscener med tre canonical anchors.",
        "narrative_progression": [
            "Etablera premiumkänslan.",
            "Avsluta i ett tydligt Golfkuponger-ögonblick.",
        ],
        "anchors": [
            {
                "position": 0,
                "label": "Öppning",
                "description": "Lugn premiumöppning över en svensk golfmiljö.",
                "role": "opening",
                "reference_requirements": [],
                "reference_note": "",
            },
            {
                "position": 1,
                "label": "Produktögonblick",
                "description": "Närmare komposition som tydligt kan bära en riktig produktreferens.",
                "role": "product",
                "reference_requirements": ["product"],
                "reference_note": "Exakt produktidentitet ska bevaras om AI används.",
            },
            {
                "position": 2,
                "label": "Avslutning",
                "description": "Ren avslutande golfkomposition med plats för tydlig branding.",
                "role": "closing",
                "reference_requirements": ["company"],
                "reference_note": "Företagsidentitet ska vara korrekt om AI används.",
            },
        ],
        "scenes": [
            {
                "position": 0,
                "title": "Premium opening move",
                "purpose": "Väck intresse",
                "narrative": "Lugn sammanhängande rörelse från K0 mot K1.",
                "start_anchor_position": 0,
                "end_anchor_position": 1,
                "duration_seconds": 5,
                "transition_intent": "Fortsätt mjukt.",
                "recipe_id": "scroll_transition_bridge",
                "recipe_version": "1.0.0",
                "recipe_name": "Scroll transition bridge",
                "recipe_reason_codes": ["trusted_recipe_registry"],
                "required_reference_roles": ["START_IMAGE", "END_IMAGE"],
                "model_capability_requirements": ["verified_model_profile", "first_last_frame"],
                "eligible_model_ids": ["bytedance/seedance-2.5"],
                "production_policy": "draft_then_final",
                "transition_to_next": {
                    "to_scene_position": 1,
                    "intent": "Fortsätt mjukt.",
                    "recipe_id": "scroll_transition_bridge",
                    "recipe_version": "1.0.0",
                    "recipe_name": "Scroll transition bridge",
                    "recipe_reason_codes": ["trusted_recipe_registry"],
                    "required_reference_roles": ["START_IMAGE", "END_IMAGE"],
                    "model_capability_requirements": ["verified_model_profile", "first_last_frame"],
                    "eligible_model_ids": ["bytedance/seedance-2.5"],
                    "production_policy": "draft_then_final",
                },
            },
            {
                "position": 1,
                "title": "Premium close",
                "purpose": "Avsluta tydligt",
                "narrative": "Fortsätt från K1 till den rena slutkompositionen K2.",
                "start_anchor_position": 1,
                "end_anchor_position": 2,
                "duration_seconds": 5,
                "transition_intent": "",
                "recipe_id": "scroll_transition_bridge",
                "recipe_version": "1.0.0",
                "recipe_name": "Scroll transition bridge",
                "recipe_reason_codes": ["trusted_recipe_registry"],
                "required_reference_roles": ["START_IMAGE", "END_IMAGE"],
                "model_capability_requirements": ["verified_model_profile", "first_last_frame"],
                "eligible_model_ids": ["bytedance/seedance-2.5"],
                "production_policy": "draft_then_final",
                "transition_to_next": None,
            },
        ],
        "company_fact_refs": [],
        "assumptions": [],
    }


def seed():
    username = "sequence-g2-audit@example.test"
    password = "G2-audit-only-2026!"
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save(update_fields=["password"])

    company = Company.objects.create(
        owner=user,
        name="Golfkuponger G2 audit",
        profile="Golfkuponger erbjuder golfrelaterade värdebevis.",
        voice="Premium och tydlig",
        current="Aktuellt fokus är enkel användning.",
        source="CI fixture",
    )
    project = create_sequence_project(
        company,
        author=user,
        title="G2 anchor materialization audit",
        brief="Premium 2-scene Golfkuponger scroll story",
        goal="Premium, tydligt och sammanhängande",
        format="scroll_story",
        platform="web",
    )
    SequenceProject.objects.filter(pk=project.pk).update(
        plan=plan(),
        plan_revision=1,
        blueprint_id="sequence_planner",
        blueprint_version="1.1.0",
    )
    project.refresh_from_db()

    k0_asset = store_asset(company, picture((27, 78, 52)), alt_text="K0 audit")
    k1_asset = store_asset(company, picture((47, 108, 72)), alt_text="K1 audit")
    k2_candidate = store_asset(company, picture((91, 140, 92)), alt_text="K2 candidate")

    k0 = materialize_planned_anchor_asset(project, k0_asset, position=0, source_type="uploaded", created_by=user)
    k1 = materialize_planned_anchor_asset(project, k1_asset, position=1, source_type="uploaded", created_by=user)
    create_clip(
        project,
        k0,
        k1,
        position=0,
        recipe_id="scroll_transition_bridge",
        label="Opening move",
        duration_seconds_target=5,
    )

    assert MediaGeneration.objects.count() == 0

    AUDIT_FILE.write_text(
        json.dumps(
            {
                "username": username,
                "password": password,
                "path": f"/company/{company.pk}/sequences/{project.pk}/",
                "project_id": str(project.pk),
                "k2_asset_id": str(k2_candidate.pk),
            }
        ),
        encoding="utf-8",
    )
    print(AUDIT_FILE.read_text(encoding="utf-8"))


def no_horizontal_overflow(page, label):
    metrics = page.evaluate(
        """() => ({
          htmlScroll: document.documentElement.scrollWidth,
          htmlClient: document.documentElement.clientWidth,
          bodyScroll: document.body.scrollWidth,
          bodyClient: document.body.clientWidth
        })"""
    )
    assert metrics["htmlScroll"] <= metrics["htmlClient"] + 2, f"{label}: html overflow {metrics}"
    assert metrics["bodyScroll"] <= metrics["bodyClient"] + 2, f"{label}: body overflow {metrics}"


def audit():
    from playwright.sync_api import sync_playwright

    data = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    base = os.environ.get("G2_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(base + data["path"], wait_until="networkidle")
        if page.locator("input[name='username']").count():
            page.locator("input[name='username']").fill(data["username"])
            page.locator("input[name='password']").fill(data["password"])
            page.get_by_role("button", name="Logga in").click()
            page.wait_for_load_state("networkidle")

        assert page.get_by_role("heading", name="Materialisera blueprintens anchors").count() == 1
        assert page.locator(".sequence-materialization-card").count() == 3
        assert page.get_by_text("2/3 klara", exact=True).count() == 1
        assert page.get_by_text("Video är låst tills blueprintens anchors finns.", exact=True).count() == 1
        assert page.locator("#planned-anchor-k2 .status-badge").inner_text().strip() == "Saknas"
        prepare = page.get_by_role("button", name="Förbered clip").first
        assert prepare.is_disabled(), "Clip prepare must be disabled while K2 is missing"
        no_horizontal_overflow(page, "desktop-before")
        page.screenshot(path=str(ARTIFACT_DIR / "desktop-before-1440.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="networkidle")
        no_horizontal_overflow(page, "mobile-before")
        cols = page.locator(".sequence-materialization-grid").evaluate(
            "el => getComputedStyle(el).gridTemplateColumns"
        )
        assert " " not in cols.strip(), f"Expected one mobile materialization column, got {cols}"
        card = page.locator("#planned-anchor-k2")
        box = card.bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390.5
        for summary in card.locator(".sequence-materialization-actions summary").all():
            sb = summary.bounding_box()
            assert sb and sb["height"] >= 43.5, f"Materialization summary below 44px: {sb}"
        page.screenshot(path=str(ARTIFACT_DIR / "mobile-before-390.png"), full_page=True)

        media_details = card.locator(".sequence-materialization-actions details").filter(
            has=page.get_by_text("Använd Media-bild", exact=True)
        )
        media_details.locator("summary").click()
        media_details.locator("select[name='asset_id']").select_option(data["k2_asset_id"])
        media_details.get_by_role("button", name="Använd på K2").click()
        page.wait_for_load_state("networkidle")

        assert page.get_by_text("Alla 3 anchors klara", exact=True).count() == 1
        assert page.get_by_text("Video är låst tills blueprintens anchors finns.", exact=True).count() == 0
        assert page.locator("#planned-anchor-k2 .status-badge").inner_text().strip() == "Canonical"
        assert not page.get_by_role("button", name="Förbered clip").first.is_disabled()
        assert page.locator("#planned-anchor-k2 img").count() == 1
        no_horizontal_overflow(page, "mobile-after")
        page.screenshot(path=str(ARTIFACT_DIR / "mobile-after-390.png"), full_page=True)
        browser.close()

    project = SequenceProject.objects.get(pk=data["project_id"])
    assert project.anchors.filter(position=2, asset_id=data["k2_asset_id"]).exists()
    assert MediaGeneration.objects.count() == 0, "Browser audit must not create provider media jobs"
    print("g2_browser_audit ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if args.seed:
        seed()
    if args.audit:
        audit()
