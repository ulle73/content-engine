import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Company, MediaGeneration, SequenceProject
from .sequence import create_sequence_project
from .sequence_planner import (
    PLANNER_ID,
    PLANNER_VERSION,
    PlannerAnchorProposal,
    PlannerFactRef,
    PlannerProposal,
    PlannerSceneProposal,
    SequencePlanError,
    generate_sequence_plan,
    update_sequence_plan,
)


def four_scene_proposal(*, fact_quote="Golfkuponger erbjuder golfrelaterade värdebevis."):
    anchors = [
        PlannerAnchorProposal(
            position=index,
            label=f"K{index}",
            description=f"Premium canonical golf anchor {index} with clear visual continuity.",
            role="opening" if index == 0 else "closing" if index == 4 else "continuity",
        )
        for index in range(5)
    ]
    scenes = [
        PlannerSceneProposal(
            position=index,
            title=f"Scene {index + 1}",
            purpose=["Väck intresse", "Visa enkelhet", "Visa användning", "Avsluta premium"][index],
            narrative=f"Visuell progression för scene {index + 1} med kontrollerad kamerarörelse.",
            start_anchor_position=index,
            end_anchor_position=index + 1,
            duration_seconds=[5, 8, 10, 5][index],
            transition_intent="Fortsätt sömlöst till nästa komposition." if index < 3 else "",
        )
        for index in range(4)
    ]
    return PlannerProposal(
        summary="En premium fyrdelad berättelse från inspiration till tydlig avslutning.",
        narrative_progression=[
            "Etablera premiumkänslan.",
            "Förklara enkelheten visuellt.",
            "Visa användningen utan nya faktapåståenden.",
            "Avsluta med ett lugnt premiumögonblick.",
        ],
        anchors=anchors,
        scenes=scenes,
        company_fact_refs=[
            PlannerFactRef(source_field="profile", quote=fact_quote)
        ] if fact_quote else [],
        assumptions=["Exakt bildspråk finjusteras när riktiga anchor-bilder väljs."],
    )


class SequencePlannerG1Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="g1-owner@example.test")
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golfkuponger erbjuder golfrelaterade värdebevis. Tjänsten används digitalt.",
            voice="Premium och tydlig",
            current="Aktuellt fokus är enkel användning och tydlig produktkommunikation.",
            source="Test",
        )
        self.project = create_sequence_project(
            self.company,
            author=self.user,
            title="Premium scroll story",
            brief="Create a premium 4-scene Golfkuponger scroll story",
            goal="Premium och enkel",
            format="scroll_story",
            platform="web",
        )

    def test_four_scene_scroll_plan_is_grounded_editable_and_creates_no_media_generation(self):
        before = MediaGeneration.objects.count()
        usage = {
            "provider": "openrouter",
            "service": "text",
            "operation": "sequence_plan",
            "model": "test-planner",
            "usage": {"total_tokens": 321},
            "cost_usd": 0.001,
        }
        with patch(
            "engine.sequence_planner.structured_generation",
            return_value=(four_scene_proposal(), usage),
        ) as generation:
            planned = generate_sequence_plan(self.project)

        generation.assert_called_once()
        self.assertEqual(MediaGeneration.objects.count(), before)
        self.assertEqual(planned.blueprint_id, PLANNER_ID)
        self.assertEqual(planned.blueprint_version, PLANNER_VERSION)
        self.assertEqual(planned.plan_revision, 1)
        self.assertEqual(planned.plan["status"], "draft")
        self.assertEqual(planned.plan["scene_count"], 4)
        self.assertEqual(len(planned.plan["anchors"]), 5)
        self.assertEqual(len(planned.plan["scenes"]), 4)
        self.assertEqual(planned.plan_usage["operation"], "sequence_plan")
        self.assertEqual(
            planned.plan["company_fact_refs"],
            [{"source_field": "profile", "quote": "Golfkuponger erbjuder golfrelaterade värdebevis."}],
        )

        for index, scene in enumerate(planned.plan["scenes"]):
            self.assertEqual(scene["position"], index)
            self.assertEqual(scene["start_anchor_position"], index)
            self.assertEqual(scene["end_anchor_position"], index + 1)
            self.assertEqual(scene["recipe_id"], "scroll_transition_bridge")
            self.assertEqual(scene["recipe_version"], "1.0.0")
            self.assertEqual(scene["required_reference_roles"], ["START_IMAGE", "END_IMAGE"])
            self.assertIn("first_last_frame", scene["model_capability_requirements"])
            self.assertIn("bytedance/seedance-2.5", scene["eligible_model_ids"])
            self.assertNotIn("kling-video/v2.5-turbo/pro", scene["eligible_model_ids"])
            if index < 3:
                self.assertEqual(scene["transition_to_next"]["recipe_id"], "scroll_transition_bridge")
            else:
                self.assertIsNone(scene["transition_to_next"])

    def test_scene_count_from_loose_brief_is_enforced_before_plan_is_saved(self):
        bad = four_scene_proposal()
        bad = bad.model_copy(update={"scenes": bad.scenes[:3]})
        with patch("engine.sequence_planner.structured_generation", return_value=(bad, {})):
            with self.assertRaisesRegex(SequencePlanError, "briefen kräver 4"):
                generate_sequence_plan(self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.plan, {})
        self.assertEqual(self.project.plan_revision, 0)

    def test_unverified_company_fact_quote_fails_closed_and_saves_nothing(self):
        proposal = four_scene_proposal(fact_quote="Golfkuponger har 5000 partnerklubbar.")
        with patch("engine.sequence_planner.structured_generation", return_value=(proposal, {})):
            with self.assertRaisesRegex(SequencePlanError, "utan verifierad källa"):
                generate_sequence_plan(self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.plan, {})
        self.assertEqual(self.project.plan_revision, 0)

    def test_edit_preserves_trusted_metadata_recomputes_models_and_can_mark_final(self):
        with patch(
            "engine.sequence_planner.structured_generation",
            return_value=(four_scene_proposal(), {"operation": "sequence_plan"}),
        ):
            planned = generate_sequence_plan(self.project)

        original_recipe = planned.plan["scenes"][0]["recipe_id"]
        original_fact_refs = planned.plan["company_fact_refs"]
        updated = update_sequence_plan(
            planned,
            {
                "status": "final",
                "summary": "Redigerad och godkänd fyrdelad plan.",
                "narrative_progression": ["Öppna", "Fördjupa", "Visa", "Avsluta"],
                "anchors": [
                    {
                        "position": 0,
                        "label": "Ny öppning",
                        "description": "En tydligare premiumöppning med ren komposition.",
                        "role": "hero",
                    }
                ],
                "scenes": [
                    {
                        "position": 0,
                        "title": "Ny Scene 1",
                        "purpose": "Tydligare öppning",
                        "narrative": "Lugn rörelse framåt mot nästa anchor.",
                        "duration_seconds": 20,
                        "transition_intent": "Mjukt och kontinuerligt.",
                        "recipe_id": "untrusted_recipe_should_be_ignored",
                        "eligible_model_ids": ["fake/model"],
                    }
                ],
            },
        )

        self.assertEqual(updated.plan_revision, 2)
        self.assertEqual(updated.plan["status"], "final")
        self.assertEqual(updated.plan["anchors"][0]["label"], "Ny öppning")
        self.assertEqual(updated.plan["scenes"][0]["duration_seconds"], 20)
        self.assertEqual(updated.plan["scenes"][0]["recipe_id"], original_recipe)
        self.assertNotIn("fake/model", updated.plan["scenes"][0]["eligible_model_ids"])
        self.assertEqual(updated.plan["company_fact_refs"], original_fact_refs)
        self.assertEqual(updated.plan_usage["operation"], "sequence_plan")

    def test_stale_editor_revision_fails_closed(self):
        with patch(
            "engine.sequence_planner.structured_generation",
            return_value=(four_scene_proposal(), {}),
        ):
            planned = generate_sequence_plan(self.project)
        stale = SequenceProject.objects.get(pk=planned.pk)
        SequenceProject.objects.filter(pk=planned.pk).update(plan_revision=planned.plan_revision + 1)
        with self.assertRaisesRegex(SequencePlanError, "annan session"):
            update_sequence_plan(
                stale,
                {
                    "status": "draft",
                    "summary": stale.plan["summary"],
                    "narrative_progression": stale.plan["narrative_progression"],
                },
            )


class SequencePlannerG1ViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="g1-ui@example.test",
            password="test-only-password",
        )
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golfkuponger erbjuder golfrelaterade värdebevis.",
            current="Aktuellt fokus är enkel användning.",
            source="Test",
        )
        self.project = create_sequence_project(
            self.company,
            author=self.user,
            title="G1 UI",
            brief="Create a premium 4-scene Golfkuponger scroll story",
            format="scroll_story",
            platform="web",
        )
        self.client.force_login(self.user)

    def test_workspace_shows_planner_before_anchor_controls(self):
        response = self.client.get(
            reverse(
                "engine:sequence_workspace",
                kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("G1 · Sequence planner", body)
        self.assertIn("Skapa en första plan", body)
        self.assertLess(body.index("G1 · Sequence planner"), body.index("Lägg till anchor"))
        self.assertIn("Ingen MediaGeneration skapas i detta steg.", body)

    def test_generate_endpoint_is_company_scoped_and_provider_media_free(self):
        with patch(
            "engine.sequence_planner.structured_generation",
            return_value=(four_scene_proposal(), {"operation": "sequence_plan"}),
        ), patch("engine.media.providers.estimate_video") as estimate, patch(
            "engine.media.providers.start_video"
        ) as start:
            response = self.client.post(
                reverse(
                    "engine:sequence_plan_generate",
                    kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk},
                ),
                {
                    "brief": "Create a premium 4-scene Golfkuponger scroll story",
                    "goal": "Premium och enkel",
                },
            )

        estimate.assert_not_called()
        start.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.plan["scene_count"], 4)
        self.assertFalse(MediaGeneration.objects.exists())

        outsider = get_user_model().objects.create_user(username="g1-outsider@example.test")
        other = Company.objects.create(owner=outsider, name="Other")
        foreign = create_sequence_project(
            other,
            author=outsider,
            title="Foreign",
            brief="Create a 4-scene story",
            format="scroll_story",
            platform="web",
        )
        response = self.client.post(
            reverse(
                "engine:sequence_plan_generate",
                kwargs={"workspace_id": self.company.pk, "project_id": foreign.pk},
            ),
            {"brief": "Create a 4-scene story"},
        )
        self.assertEqual(response.status_code, 404)

    def test_saved_plan_renders_editable_storyboard_and_trusted_metadata(self):
        with patch(
            "engine.sequence_planner.structured_generation",
            return_value=(four_scene_proposal(), {"operation": "sequence_plan"}),
        ):
            generate_sequence_plan(self.project)

        response = self.client.get(
            reverse(
                "engine:sequence_workspace",
                kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk},
            )
        )
        self.assertContains(response, "Editable blueprint")
        self.assertContains(response, "4 scenes · 5 anchors")
        self.assertContains(response, 'name="anchor_0_description"', html=False)
        self.assertContains(response, 'name="scene_0_narrative"', html=False)
        self.assertContains(response, 'name="status"', html=False)
        self.assertContains(response, "scroll_transition_bridge")
        self.assertContains(response, "START_IMAGE, END_IMAGE")
        self.assertContains(response, "bytedance/seedance-2.5")
        self.assertContains(response, "Verifierade fakta som användes")

    def test_save_endpoint_updates_editable_fields_but_not_trusted_recipe(self):
        with patch(
            "engine.sequence_planner.structured_generation",
            return_value=(four_scene_proposal(), {"operation": "sequence_plan"}),
        ):
            planned = generate_sequence_plan(self.project)
        original_recipe = planned.plan["scenes"][0]["recipe_id"]

        post = {
            "status": "final",
            "summary": "Final plan",
            "narrative_progression": "Öppna\nFördjupa\nVisa\nAvsluta",
        }
        for anchor in planned.plan["anchors"]:
            position = anchor["position"]
            post[f"anchor_{position}_label"] = anchor["label"]
            post[f"anchor_{position}_description"] = anchor["description"]
            post[f"anchor_{position}_role"] = anchor["role"]
        for scene in planned.plan["scenes"]:
            position = scene["position"]
            post[f"scene_{position}_title"] = "Redigerad scene" if position == 0 else scene["title"]
            post[f"scene_{position}_purpose"] = scene["purpose"]
            post[f"scene_{position}_narrative"] = scene["narrative"]
            post[f"scene_{position}_duration"] = str(scene["duration_seconds"])
            post[f"scene_{position}_transition"] = scene["transition_intent"]

        response = self.client.post(
            reverse(
                "engine:sequence_plan_save",
                kwargs={"workspace_id": self.company.pk, "project_id": self.project.pk},
            ),
            post,
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.plan["status"], "final")
        self.assertEqual(self.project.plan["scenes"][0]["title"], "Redigerad scene")
        self.assertEqual(self.project.plan["scenes"][0]["recipe_id"], original_recipe)
        self.assertEqual(self.project.plan_revision, 2)
