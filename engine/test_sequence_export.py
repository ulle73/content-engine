import io
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .creative_core import ReferenceRole
from .forms import snapshot_company_context
from .media import store_asset
from .media_references import add_generation_reference
from .models import Company, ContentRun, MediaAsset, MediaGeneration, SequenceClipVersion
from .motion import service
from .motion.models import MotionProject
from .sequence import add_anchor, create_clip, create_sequence_project
from .sequence_export import FilmForm, compile_film, prepare_film


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class SequenceFilmTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        override = override_settings(MEDIA_ROOT=Path(self.directory.name))
        override.enable()
        self.addCleanup(override.disable)
        self.user = get_user_model().objects.create_user(username="film", password="test")
        self.company = Company.objects.create(owner=self.user, name="Film company")
        self.other = Company.objects.create(owner=get_user_model().objects.create_user(username="other-film"), name="Other")
        self.run = ContentRun.objects.create(workspace=self.company, author=self.user, model="fixture",
            context=snapshot_company_context(self.company), draft={"facebook": "Min text", "instagram": "Min text"})
        self.sequence = create_sequence_project(self.company, author=self.user, title="Min film", source_run=self.run)
        self.anchors = [add_anchor(self.sequence, self.image(color), position=i) for i, color in enumerate(["green", "blue"])]
        self.settings = {"mode": "images", "headline": "Spela mer golf", "cta": "Hitta nästa runda", "music": "none", "aspect_ratio": "9:16"}
        self.client.force_login(self.user)

    def image(self, color, size=(1080, 1080)):
        output = io.BytesIO()
        Image.new("RGB", size, color).save(output, "PNG")
        return store_asset(self.company, output.getvalue())

    def prepare(self, revision=0, key="film-prepare-1", settings=None):
        return prepare_film(self.company, self.user, self.sequence.pk, settings=settings or self.settings,
            expected_revision=revision, key=key)

    def selected_clip(self, start, end, position):
        clip = create_clip(self.sequence, start, end, position=position, recipe_id="scroll_transition_bridge")
        generation = MediaGeneration.objects.create(run=self.run, kind="video", provider="fixture", status="completed", prompt="", parameters={})
        add_generation_reference(generation, start.asset, role=ReferenceRole.start_image, position=0)
        add_generation_reference(generation, end.asset, role=ReferenceRole.end_image, position=0)
        version = SequenceClipVersion.objects.create(clip=clip, generation=generation, version_number=1,
            status="selected", recipe_id=clip.recipe_id, recipe_version=clip.recipe_version)
        clip.selected_version = version
        clip.status = "selected"
        clip.save()
        MediaAsset.objects.create(company=self.company, generation=generation, kind="video", purpose="content",
            origin="generated", mime_type="video/mp4", width=1080, height=1920, duration_seconds=2.0,
            byte_size=1000, sha256="a" * 64, storage_key=f"fixture/{generation.pk}.mp4")
        return clip

    def test_prepare_preserves_content_and_is_idempotent(self):
        project = self.prepare()
        self.assertEqual(project.pk, self.prepare().pk)
        self.assertEqual(project.run_id, self.run.pk)
        self.assertEqual(project.run.draft["facebook"], "Min text")
        self.assertEqual(project.revisions.count(), 1)
        spec = project.revisions.get().spec
        self.assertEqual([s["component"] for s in spec["scenes"]], ["footage", "footage", "end-card"])
        self.assertFalse(spec["audio"]["enabled"])
        self.assertEqual(sum(s["duration_frames"] for s in spec["scenes"]), 360)

    def test_changed_settings_create_revision_and_clear_approval(self):
        project = self.prepare()
        changed = dict(self.settings, music="bed")
        project = self.prepare(revision=1, key="film-music-2", settings=changed)
        self.assertEqual(project.current_revision, 2)
        self.assertEqual(project.revisions.get(number=1).spec["audio"]["music"], "none")
        self.assertTrue(project.revisions.get(number=2).spec["audio"]["enabled"])
        self.assertEqual(project.pk, self.prepare(revision=2, key="film-no-change-3", settings=changed).pk)
        self.assertEqual(project.revisions.count(), 2)
        with self.assertRaisesMessage(ValueError, "ändrats"):
            self.prepare(revision=1, key="film-old-version-4")

    def test_source_changes_block_old_render(self):
        project = self.prepare()
        add_anchor(self.sequence, self.image("red"), position=2)
        with self.assertRaisesMessage(ValueError, "material har ändrats"):
            service.queue_render(self.company, self.user, project.pk, mode="preview", expected_revision=1, key="stale-preview-1")
        project = self.prepare(revision=1, key="film-new-material-2")
        self.assertEqual(project.current_revision, 2)
        self.assertEqual(len(project.revisions.get(number=2).spec["scenes"]), 4)

    def test_cannot_bypass_source_guard_with_generic_mcp_update(self):
        project = self.prepare()
        with self.assertRaisesMessage(ValueError, "sekvensen"):
            service.update_project(self.company, self.user, project.pk, spec=project.revisions.get().spec,
                expected_revision=1, key="generic-update-denied")

    def test_small_or_expired_images_are_rejected(self):
        small = self.image("red", (80, 80))
        self.anchors[0].asset = small
        self.anchors[0].save()
        with self.assertRaisesMessage(ValueError, "för liten"):
            self.prepare()
        small.width = small.height = 1080
        small.expires_at = timezone.now() - timedelta(seconds=1)
        small.save()
        with self.assertRaisesMessage(ValueError, "gått ut"):
            self.prepare()
        self.assertFalse(MotionProject.objects.exists())

    def test_company_and_content_isolation(self):
        with self.assertRaisesMessage(ValueError, "detta företag"):
            prepare_film(self.other, self.other.owner, self.sequence.pk, settings=self.settings, expected_revision=0, key="other-film-1")
        with self.assertRaises(ValueError):
            create_sequence_project(self.other, title="No", source_run=self.run)

    def test_form_rejects_overlong_text_and_preserves_input(self):
        form = FilmForm(dict(self.settings, cta=" ".join(["ord"] * 13)))
        self.assertFalse(form.is_valid())
        self.assertIn("cta", form.errors)
        self.assertEqual(form.data["cta"].split(), ["ord"] * 13)

    def test_long_messages_get_reading_time_without_slowing_video_clips(self):
        settings = dict(self.settings, headline=" ".join(["golf"] * 12), cta=" ".join(["spel"] * 12))
        spec = compile_film(self.sequence, settings)
        self.assertGreater(spec["scenes"][0]["duration_frames"], 120)
        self.assertGreater(spec["scenes"][-1]["duration_frames"], 240)
        self.assertEqual(spec["scenes"][-1]["props"]["eyebrow"], self.company.name)

    def test_sequence_creation_preserves_source_run_through_post(self):
        url = reverse("engine:sequence_list", kwargs={"workspace_id": self.company.pk})
        response = self.client.post(url, {"run_id": str(self.run.pk), "title": "Ny film", "brief": "Min brief", "format": "reel", "platform": "instagram"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.company.sequence_projects.get(title="Ny film").source_run_id, self.run.pk)

    def test_selected_clips_export_in_order_and_reject_stale_versions(self):
        first = self.selected_clip(self.anchors[0], self.anchors[1], 0)
        third = add_anchor(self.sequence, self.image("red"), position=2)
        self.selected_clip(self.anchors[1], third, 1)
        spec = compile_film(self.sequence, dict(self.settings, mode="clips"))
        self.assertEqual([s["duration_frames"] for s in spec["scenes"]], [60, 60, 120])
        first.selected_version.status = "stale"
        first.selected_version.save()
        with self.assertRaisesMessage(ValueError, "Granska och välj"):
            compile_film(self.sequence, dict(self.settings, mode="clips"))

    def test_missing_continuity_is_rejected(self):
        self.selected_clip(self.anchors[0], self.anchors[1], 0)
        third = add_anchor(self.sequence, self.image("red"), position=2)
        fourth = add_anchor(self.sequence, self.image("yellow"), position=3)
        self.selected_clip(third, fourth, 1)
        with self.assertRaisesMessage(ValueError, "övergång"):
            compile_film(self.sequence, dict(self.settings, mode="clips"))

    def test_ui_prepare_errors_and_safe_flow(self):
        url = reverse("engine:sequence_film_prepare", kwargs={"workspace_id": self.company.pk, "project_id": self.sequence.pk})
        response = self.client.post(url, dict(self.settings, revision="0", key="web-film-prepare"))
        self.assertEqual(response.status_code, 302)
        project = MotionProject.objects.get()
        response = self.client.get(response.url)
        self.assertContains(response, "Klippljud är avstängt")
        self.assertNotContains(response, "Redigera specifikationen via MCP")
        self.assertEqual(project.run_id, self.run.pk)
        response = self.client.post(url, dict(self.settings, revision="0", key="web-film-stale"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Öppna sekvensen igen", status_code=400)

    def test_final_still_requires_preview(self):
        project = self.prepare()
        with self.assertRaisesMessage(ValueError, "förhandsvisning"):
            service.queue_render(self.company, self.user, project.pk, mode="final", expected_revision=1, key="film-final-blocked")

    def test_incomplete_plan_cannot_silently_become_a_partial_film(self):
        self.sequence.plan = {"planner_id": "sequence_planner", "anchors": [{"position": 0}, {"position": 1}, {"position": 2}]}
        self.sequence.save()
        with self.assertRaisesMessage(ValueError, "Saknas: K2"):
            self.prepare()

    def test_mcp_reuses_the_same_film_service_and_scope(self):
        from engine import mcp_server
        registered = lambda name: mcp_server.mcp._tool_manager.get_tool(name).fn
        token = SimpleNamespace(claims={"django_user_id": self.user.pk})
        with patch("engine.mcp_auth.get_access_token", return_value=token):
            data = registered("prepare_sequence_film")(str(self.company.pk), str(self.sequence.pk), self.settings, 0, "mcp-film-shared-1")
            project = MotionProject.objects.get(pk=data["project_id"])
            self.assertEqual(data["source_sequence_id"], str(self.sequence.pk))
            self.assertEqual(project.run_id, self.run.pk)
            self.assertEqual(data["spec"], compile_film(self.sequence, self.settings))
            self.assertEqual(registered("list_video_sequences")(str(self.company.pk))[0]["film_revision"], 1)
            with self.assertRaises(mcp_server.ToolError):
                registered("prepare_sequence_film")(str(self.other.pk), str(self.sequence.pk), self.settings, 0, "mcp-other-film-1")
