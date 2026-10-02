"""Regression coverage for the novice-friendly composer and shared planner."""
import io
import os
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .creative_budget import known_video_cost
from .creative_director import build_plan, parse_brief
from .creative_registry import registry
from .forms import MediaCreationForm, snapshot_company_context
from .media import create_job, default_brief, store_asset
from .media_providers import _seedance25_description_estimate
from .media_storage import MediaError
from .models import Company, ContentRun, MediaAsset, MediaGeneration


@override_settings(MEDIA_STORAGE="local")
class ProductFlowTests(TestCase):
    def setUp(self):
        self.storage = TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        setting = override_settings(MEDIA_ROOT=Path(self.storage.name))
        setting.enable()
        self.addCleanup(setting.disable)
        self.user = get_user_model().objects.create_user(username="flow-owner")
        self.company = Company.objects.create(
            owner=self.user, name="Demo", profile="Product studio", voice="Friendly",
            current="Synthetic facts", source="Local fixture",
            valid_until=timezone.localdate() + timedelta(days=30),
        )
        self.run = ContentRun.objects.create(
            workspace=self.company, author=self.user, model="test",
            context=snapshot_company_context(self.company), selected=0,
            ideas=[{"title": "A product", "photo_brief": "Old image idea", "angle": "Product details"}],
            draft={"photo_brief": "A white product on a table in morning light.", "instagram": "Keep copy", "facebook": "Keep Facebook copy"},
        )
        self.client.force_login(self.user)

    def asset(self, company=None):
        out = io.BytesIO()
        Image.new("RGB", (96, 160), (210, 225, 230)).save(out, "PNG")
        return store_asset(company or self.company, out.getvalue(), alt_text="Demo product")

    def url(self, name, **kwargs):
        return reverse("engine:" + name, kwargs={"workspace_id": self.company.pk, "run_id": self.run.pk, **kwargs})

    def payload(self, **kwargs):
        return {"token": str(uuid.uuid4()), "kind": "image", "brief": "My own product idea", "count": "1", "priority": "balanced", "shape": "portrait", **kwargs}

    def test_default_uses_latest_saved_visual_intent_for_image_and_video(self):
        for kind in ("image", "video"):
            self.assertEqual(default_brief(self.run, kind), self.run.draft["photo_brief"])

    def test_default_video_passes_its_own_planner(self):
        plan = build_plan(self.run, default_brief(self.run, "video"), kind="video")
        self.assertFalse([issue for issue in plan.preflight if issue.severity == "error"])

    def test_recipe_default_duration_and_explicit_duration(self):
        source = self.asset()
        plan = build_plan(self.run, "A calm premium product reveal.", kind="video", source=source, recipe_id="premium_product_reveal")
        self.assertEqual(plan.brief.duration_seconds, 8)
        explicit = build_plan(self.run, "A calm premium product reveal, 5 seconds.", kind="video", source=source, recipe_id="premium_product_reveal")
        self.assertEqual(explicit.brief.duration_seconds, 5)

    @patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "2"})
    def test_auto_recipe_default_fits_real_local_pricing_rule_without_provider_io(self):
        with patch("httpx.Client.send", side_effect=AssertionError("no network")):
            plan = build_plan(self.run, "A calm premium product reveal.", kind="video",
                              source=self.asset(), recipe_id="premium_product_reveal")
            self.assertEqual(plan.parameters["duration"], 8)
            self.assertEqual(plan.parameters["resolution"], "480p")
            estimate = _seedance25_description_estimate(
                plan.parameters["provider_model"], plan.parameters,
                {"type": "description", "pricing_description": "video tokens 0.0214 480p 720p"},
            )
        self.assertEqual(estimate["estimate"]["usd"], "1.6448")
        self.assertTrue(any(issue.code == "resolution_budget_adjusted" for issue in plan.preflight))
        self.assertFalse(MediaGeneration.objects.exists())

    @patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "2"})
    def test_auto_skips_known_over_budget_model_preserving_exact_duration(self):
        plan = build_plan(self.run, "A product for 10 seconds", kind="video")
        self.assertEqual(plan.parameters["duration"], 10)
        self.assertEqual(plan.selection.model_id, "kling-video/v2.5-turbo/pro")
        self.assertIsNone(known_video_cost(plan.selection.model_id, 10, "720p"))

    @patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "2"})
    def test_explicit_over_budget_seedance_settings_rejected_before_job_or_provider(self):
        with patch("engine.media.providers.estimate_video") as estimate, \
             patch("engine.media.providers.start_video") as paid:
            response = self.client.post(self.url("media_generate"), self.payload(
                kind="video", brief="A product for 8 seconds", resolution="720p",
                model_override="bytedance/seedance-2.5"))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.context["creator_form"]["resolution"].value(), "720p")
        self.assertFalse(MediaGeneration.objects.exists())
        estimate.assert_not_called()
        paid.assert_not_called()

    @patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "4"})
    def test_auto_retains_720p_when_configured_budget_allows_it(self):
        plan = build_plan(self.run, "A product for 8 seconds", kind="video")
        self.assertEqual(plan.parameters["resolution"], "720p")
        self.assertFalse(any(issue.code == "resolution_budget_adjusted" for issue in plan.preflight))

    @patch.dict(os.environ, {"HIGGSFIELD_MAX_USD": "2"})
    def test_long_request_is_not_shortened_to_evade_budget(self):
        only_known = tuple(item for item in registry() if item.model_id == "bytedance/seedance-2.5")
        with patch("engine.creative_registry.registry", return_value=only_known), \
             self.assertRaisesRegex(ValueError, "kostnadsgräns"):
            build_plan(self.run, "A product for 20 seconds", kind="video")

    def test_motion_conflict_keeps_user_choices_and_starts_nothing(self):
        with patch("httpx.Client.send", side_effect=AssertionError("no network")):
            response = self.client.post(self.url("creation_preview"), self.payload(
                kind="video", brief="Bollen lyfter.", subject_motion="still"))
            self.assertEqual(response.status_code, 422)
            self.assertIn("rörelseval", response.json()["error"])
            response = self.client.post(self.url("media_generate"), self.payload(
                kind="video", brief="Bollen lyfter.", subject_motion="still"))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.context["creator_form"]["subject_motion"].value(), "still")
        self.assertEqual(response.context["creator_form"]["brief"].value(), "Bollen lyfter.")
        self.assertFalse(MediaGeneration.objects.exists())

    def test_recipe_defaults_and_controls_match_free_preview_and_review(self):
        source = self.asset()
        payload = self.payload(kind="video", source_asset=str(source.pk), recipe_id="premium_product_reveal",
                               brief="Static camera on a premium product.", camera="static")
        with patch("httpx.Client.send", side_effect=AssertionError("No external planning call")):
            preview = self.client.post(self.url("creation_preview"), payload)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["duration"], 8)
        self.assertFalse(MediaGeneration.objects.exists())
        with patch("engine.media.providers.estimate_video", side_effect=MediaError("Synthetic unavailable")), \
             patch("engine.media.providers.start_video") as paid:
            response = self.client.post(self.url("media_generate"), payload)
        self.assertEqual(response.status_code, 302)
        job = MediaGeneration.objects.get()
        self.assertEqual(job.prompt, preview.json()["prompt"])
        self.assertEqual(job.parameters["duration"], 8)
        camera = next(line for line in job.prompt.splitlines() if line.startswith("CAMERA:"))
        self.assertIn("static", camera)
        self.assertNotIn("push", camera.lower())
        paid.assert_not_called()

    def test_retry_restores_legacy_recipe_and_shape_without_creator_metadata(self):
        source, end = self.asset(), self.asset()
        job = create_job(self.run, token=uuid.uuid4(), kind="video", brief="A product", source=source,
                         end_source=end, recipe_id="before_after", shape="landscape", priority="quality")
        job.parameters.pop("creator")
        job.save(update_fields=["parameters"])
        response = self.client.get(self.url("media"), {"retry": str(job.pk)})
        form = response.context["creator_form"]
        self.assertEqual(form["recipe_id"].value(), "before_after")
        self.assertEqual(form["shape"].value(), "landscape")
        self.assertEqual(str(form["source_asset"].value()), str(source.pk))
        self.assertEqual(str(form["end_asset"].value()), str(end.pk))
        self.assertFalse(response.context["restore_creator"])

    def test_explicit_camera_is_not_duplicated_as_subject_motion(self):
        brief = parse_brief("Static camera. Let the flag move.", kind="video")
        self.assertEqual(brief.camera_movement, ["static"])
        self.assertNotIn("static", brief.allow_change)
        self.assertIn("flag movement", brief.allow_change)

    def test_recipe_does_not_override_explicit_static_camera(self):
        plan = build_plan(self.run, "Static camera on the product.", kind="video", source=self.asset(), recipe_id="premium_product_reveal")
        camera = next(line for line in plan.prompt.splitlines() if line.startswith("CAMERA:"))
        self.assertIn("static", camera)
        self.assertNotIn("push", camera.lower())
        self.assertNotIn("orbit", camera.lower())

    def test_ui_starts_with_one_image_and_auto_balanced(self):
        response = self.client.get(self.url("media"))
        form = response.context["creator_form"]
        self.assertEqual(form["count"].value(), 1)
        self.assertEqual(form["priority"].value(), "balanced")
        self.assertEqual(form["model_override"].value(), "")
        self.assertEqual(form["brief"].value(), self.run.draft["photo_brief"])
        self.assertContains(response, 'id="creator-form"')

    def test_invalid_post_keeps_brief_frames_and_settings_without_job(self):
        source = self.asset()
        payload = self.payload(kind="video", source_asset=str(source.pk), recipe_id="before_after", priority="quality", shape="landscape")
        with patch("engine.media.providers.estimate_video") as estimate, patch("engine.media.providers.start_video") as paid:
            response = self.client.post(self.url("media_generate"), payload)
        self.assertEqual(response.status_code, 422)
        form = response.context["creator_form"]
        for name in ("brief", "source_asset", "recipe_id", "priority", "shape"):
            self.assertEqual(form[name].value(), payload[name])
        self.assertIn("end_asset", form.errors)
        self.assertFalse(MediaGeneration.objects.exists())
        estimate.assert_not_called()
        paid.assert_not_called()

    def test_unknown_recipe_kind_model_and_token_fail_before_generation(self):
        for invalid in ({"recipe_id": "untrusted"}, {"kind": "audio"}, {"model_override": "unknown-model"}, {"token": "not-uuid"}):
            with self.subTest(invalid=invalid):
                response = self.client.post(self.url("media_generate"), self.payload(**invalid))
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.context["creator_form"]["brief"].value(), "My own product idea")
                self.assertFalse(MediaGeneration.objects.exists())

    def test_start_end_pair_is_validated_on_server_without_javascript(self):
        end = self.asset()
        response = self.client.post(self.url("media_generate"), self.payload(kind="video", end_asset=str(end.pk)))
        self.assertEqual(response.status_code, 422)
        self.assertIn("end_asset", response.context["creator_form"].errors)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_reference_choices_are_company_scoped_and_unexpired(self):
        owner = get_user_model().objects.create_user(username="other-owner")
        other = Company.objects.create(owner=owner, name="Other")
        foreign, expired = self.asset(other), self.asset()
        MediaAsset.objects.filter(pk=expired.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        for source in (foreign, expired):
            response = self.client.post(self.url("media_generate"), self.payload(source_asset=str(source.pk)))
            self.assertEqual(response.status_code, 422)
            self.assertIn("source_asset", response.context["creator_form"].errors)
        form = self.client.get(self.url("media")).context["creator_form"]
        self.assertFalse(form.fields["source_asset"].queryset.filter(pk=foreign.pk).exists())
        self.assertFalse(form.fields["source_asset"].queryset.filter(pk=expired.pk).exists())
        self.assertFalse(MediaGeneration.objects.exists())

    def test_older_selected_frame_survives_bounded_picker(self):
        source = self.asset()
        now = timezone.now()
        # Storage access is unnecessary for the unselected option fixtures.
        MediaAsset.objects.bulk_create([MediaAsset(company=self.company, kind="image", mime_type="image/png", origin="uploaded", purpose="content", storage_key=f"fixture-{i}", byte_size=0) for i in range(121)])
        MediaAsset.objects.filter(pk=source.pk).update(created_at=now-timedelta(days=10))
        response = self.client.get(self.url("media"), {"source": str(source.pk)})
        self.assertEqual(response.context["source"].pk, source.pk)
        self.assertTrue(response.context["creator_form"].fields["source_asset"].queryset.filter(pk=source.pk).exists())

    def test_all_video_presets_compile_with_existing_trusted_recipes(self):
        source, end = self.asset(), self.asset()
        for recipe in ("premium_product_reveal", "landscape_environment_hero", "before_after", "scroll_orbit_hero"):
            with self.subTest(recipe=recipe):
                frame_end = end if recipe in {"before_after", "scroll_orbit_hero"} else None
                form = MediaCreationForm(self.payload(kind="video", recipe_id=recipe, source_asset=str(source.pk), end_asset=str(frame_end.pk) if frame_end else ""), company=self.company)
                self.assertTrue(form.is_valid(), form.errors)
                plan = build_plan(self.run, form.cleaned_data["brief"], kind="video", source=source, end_source=frame_end, recipe_id=recipe)
                self.assertFalse([issue for issue in plan.preflight if issue.severity == "error"])
                self.assertEqual(plan.brief.user_intent, "My own product idea")

    def test_web_review_uses_recipe_without_paid_call_and_is_idempotent(self):
        source, end = self.asset(), self.asset()
        payload = self.payload(kind="video", source_asset=str(source.pk), end_asset=str(end.pk), recipe_id="before_after")
        def estimate(job):
            model = job.parameters["provider_model"]
            return model, {"prompt": job.prompt}, {"estimate": {"usd": "0.80"}, "model": model}
        with patch("engine.media.providers.estimate_video", side_effect=estimate), patch("engine.media.providers.start_video") as paid:
            first = self.client.post(self.url("media_generate"), payload)
            second = self.client.post(self.url("media_generate"), payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first.url, second.url)
        self.assertEqual(MediaGeneration.objects.count(), 1)
        job = MediaGeneration.objects.get()
        self.assertEqual(job.parameters["creative"]["recipe"]["recipe_id"], "before_after")
        self.assertEqual(job.brief, payload["brief"])
        self.assertEqual(job.status, "queued")
        self.assertTrue(job.usage.get("reviewed_at"))
        paid.assert_not_called()

    def test_failed_estimate_does_not_start_or_drop_review(self):
        with patch("engine.media.providers.estimate_video", side_effect=MediaError("Synthetic unavailable")), patch("engine.media.providers.start_video") as paid:
            response = self.client.post(self.url("media_generate"), self.payload(kind="video"))
        self.assertEqual(response.status_code, 302)
        job = MediaGeneration.objects.get()
        self.assertEqual(job.status, "queued")
        self.assertFalse(job.usage.get("reviewed_at"))
        paid.assert_not_called()

    def test_retry_restores_image_count_priority_and_format(self):
        job = create_job(self.run, token=uuid.uuid4(), kind="image", brief="A product", count=3, shape="landscape", priority="economy")
        form = self.client.get(self.url("media"), {"retry": str(job.pk)}).context["creator_form"]
        self.assertEqual(form["count"].value(), 3)
        self.assertEqual(form["shape"].value(), "landscape")
        self.assertEqual(form["priority"].value(), "economy")
        self.assertNotEqual(str(form["token"].value()), str(job.pk))

    def test_retry_restores_video_recipe_and_frames(self):
        source, end = self.asset(), self.asset()
        job = create_job(self.run, token=uuid.uuid4(), kind="video", brief="A product", source=source, end_source=end, recipe_id="before_after", priority="quality")
        response = self.client.get(self.url("media"), {"retry": str(job.pk)})
        form = response.context["creator_form"]
        self.assertEqual(form["recipe_id"].value(), "before_after")
        self.assertEqual(str(form["source_asset"].value()), str(source.pk))
        self.assertEqual(str(form["end_asset"].value()), str(end.pk))
        self.assertTrue(not response.context["restore_creator"])

    def test_handoff_preserves_copy_facts_and_existing_run(self):
        original_context, original_ideas = self.run.context.copy(), self.run.ideas.copy()
        for target in ("sequence", "motion"):
            response = self.client.post(self.url("media_handoff"), {"target": target, "brief": "Updated visual idea"}, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["source_run" if target == "sequence" else "run"].pk, self.run.pk)
            self.run.refresh_from_db()
            self.assertEqual(self.run.draft["photo_brief"], "Updated visual idea")
            self.assertEqual(self.run.draft["instagram"], "Keep copy")
            self.assertEqual(self.run.draft["facebook"], "Keep Facebook copy")
            self.assertEqual(self.run.context, original_context)
            self.assertEqual(self.run.ideas, original_ideas)
        self.assertEqual(ContentRun.objects.count(), 1)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_handoff_requires_post_csrf_access_and_draft(self):
        url = self.url("media_handoff")
        self.assertEqual(self.client.get(url).status_code, 405)
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.user)
        self.assertEqual(guarded.post(url, {"target": "motion", "brief": "Idea"}).status_code, 403)
        for payload in ({"target": "https://untrusted.invalid", "brief": "Idea"}, {"target": "motion", "brief": ""}):
            self.assertEqual(self.client.post(url, payload).status_code, 400)
        outsider = get_user_model().objects.create_user(username="outsider")
        self.client.force_login(outsider)
        self.assertEqual(self.client.post(url, {"target": "motion", "brief": "Idea"}).status_code, 404)
        self.client.force_login(self.user)
        self.run.delivery_status = "delivered"
        self.run.save(update_fields=["delivery_status"])
        self.assertEqual(self.client.post(url, {"target": "motion", "brief": "Idea"}).status_code, 409)
        self.run.refresh_from_db()
        self.assertEqual(self.run.draft["photo_brief"], "A white product on a table in morning light.")

    def test_prompt_and_template_text_are_escaped_in_form(self):
        hostile = '<script>alert("x")</script> & my product'
        response = self.client.post(self.url("media_generate"), self.payload(brief=hostile, recipe_id="untrusted"))
        self.assertNotContains(response, '<script>alert("x")</script>', status_code=422)
        self.assertEqual(response.context["creator_form"]["brief"].value(), hostile)
