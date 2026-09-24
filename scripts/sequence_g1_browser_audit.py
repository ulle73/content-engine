#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")

import django

django.setup()

from django.contrib.auth import get_user_model

from engine.models import Company
from engine.sequence import create_sequence_project
from engine.sequence_planner import (
    PlannerAnchorProposal,
    PlannerFactRef,
    PlannerProposal,
    PlannerSceneProposal,
    generate_sequence_plan,
)


AUDIT_FILE = Path(".g1-audit.json")
ARTIFACT_DIR = Path("artifacts/sequence-g1")


def proposal():
    return PlannerProposal(
        summary="En premium fyrdelad berättelse från inspiration till enkel användning.",
        narrative_progression=[
            "Etablera premiumkänslan.",
            "Förflytta berättelsen mot enkelhet.",
            "Visa användning utan nya faktapåståenden.",
            "Avsluta med en tydlig premiumkänsla.",
        ],
        anchors=[
            PlannerAnchorProposal(
                position=index,
                label=f"K{index} premium anchor",
                description=(
                    f"Canonical keyframe {index} med tydlig golfmiljö, lugn komposition och visuell kontinuitet."
                ),
                role="opening" if index == 0 else "closing" if index == 4 else "continuity",
            )
            for index in range(5)
        ],
        scenes=[
            PlannerSceneProposal(
                position=index,
                title=f"Scene {index + 1}: premium progression",
                purpose=["Väck intresse", "Visa enkelhet", "Visa användning", "Avsluta tydligt"][index],
                narrative=(
                    "En kontrollerad visuell rörelse genom golfmiljön där kompositionen förflyttas "
                    f"mot nästa anchor utan hårda klipp. Del {index + 1}."
                ),
                start_anchor_position=index,
                end_anchor_position=index + 1,
                duration_seconds=[5, 8, 10, 5][index],
                transition_intent="Sömlös kontinuitet med lugn acceleration." if index < 3 else "",
            )
            for index in range(4)
        ],
        company_fact_refs=[
            PlannerFactRef(
                source_field="profile",
                quote="Golfkuponger erbjuder golfrelaterade värdebevis.",
            )
        ],
        assumptions=["Exakt visuellt uttryck finjusteras när riktiga anchors väljs."],
    )


def seed():
    username = "sequence-g1-audit@example.test"
    password = "G1-audit-only-2026!"
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save(update_fields=["password"])

    company, _ = Company.objects.get_or_create(
        owner=user,
        defaults={
            "name": "Golfkuponger G1 audit",
            "profile": "Golfkuponger erbjuder golfrelaterade värdebevis. Tjänsten används digitalt.",
            "voice": "Premium och tydlig",
            "current": "Aktuellt fokus är enkel användning och tydlig produktkommunikation.",
            "source": "CI fixture",
        },
    )
    project = create_sequence_project(
        company,
        author=user,
        title="Premium Golfkuponger 4-scene scroll story",
        brief="Create a premium 4-scene Golfkuponger scroll story",
        goal="Premium, tydligt och enkelt",
        format="scroll_story",
        platform="web",
    )
    with patch(
        "engine.sequence_planner.structured_generation",
        return_value=(
            proposal(),
            {
                "provider": "openrouter",
                "service": "text",
                "operation": "sequence_plan",
                "model": "browser-audit-fixture",
                "usage": {},
                "cost_usd": 0,
            },
        ),
    ):
        project = generate_sequence_plan(project)

    AUDIT_FILE.write_text(
        json.dumps(
            {
                "username": username,
                "password": password,
                "path": f"/company/{company.pk}/sequences/{project.pk}/",
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
    base = os.environ.get("G1_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
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

        assert page.get_by_role("heading", name="Planera hela berättelsen före media").count() == 1
        assert page.get_by_text("4 scenes · 5 anchors", exact=True).count() == 1
        assert page.locator(".sequence-plan-scene").count() == 4
        assert page.locator(".sequence-plan-anchor-card").count() == 5
        planner_y = page.locator(".sequence-planner-section").bounding_box()["y"]
        anchor_y = page.locator(".sequence-anchor-control-section").bounding_box()["y"]
        assert planner_y < anchor_y
        no_horizontal_overflow(page, "desktop")
        page.screenshot(path=str(ARTIFACT_DIR / "desktop-1440.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="networkidle")
        no_horizontal_overflow(page, "mobile")
        columns = page.locator(".sequence-plan-scene-grid").first.evaluate(
            "el => getComputedStyle(el).gridTemplateColumns"
        )
        assert " " not in columns.strip(), f"Expected one mobile scene column, got {columns}"
        planner_box = page.locator(".sequence-planner-section").bounding_box()
        assert planner_box and planner_box["x"] >= 0 and planner_box["x"] + planner_box["width"] <= 390.5

        for selector in (
            ".sequence-plan-generate-actions button",
            ".sequence-plan-save-row button",
        ):
            target = page.locator(selector).first
            box = target.bounding_box()
            assert box and box["height"] >= 43.5, f"Target below 44px: {selector} => {box}"

        page.locator("#sequence-plan-summary").fill("Browser-verifierad final plan")
        page.locator(".sequence-plan-status-control select").select_option("final")
        page.get_by_role("button", name="Spara planändringar").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#sequence-plan-summary").input_value() == "Browser-verifierad final plan"
        assert page.locator(".sequence-plan-status-control select").input_value() == "final"
        assert page.get_by_text("Final · V2", exact=True).count() == 1
        no_horizontal_overflow(page, "mobile-after-save")
        page.screenshot(path=str(ARTIFACT_DIR / "mobile-390.png"), full_page=True)

        browser.close()
        print("g1_browser_audit ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if args.seed:
        seed()
    if args.audit:
        audit()
