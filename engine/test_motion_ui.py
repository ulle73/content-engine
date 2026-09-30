import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from engine.media import select_asset
from engine.media_storage import MediaError
from engine.models import Company, ContentRun, MediaAsset, MediaGeneration
from engine.motion import service
from engine.motion.models import MotionKeyframe, MotionProject
from engine.motion.planner import compile_template
from engine.operator_common import OperatorError
from engine.operator_media import media_options, select_run_asset


class MotionProductTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="motion-ui", password="test")
        self.company = Company.objects.create(
            owner=self.user, name="Golfkuponger", profile="Golf", current="Mer golf", source="Testunderlag",
            valid_until=timezone.localdate() + timedelta(days=30),
        )
        self.other = Company.objects.create(owner=get_user_model().objects.create_user(username="other"), name="Other")
        self.run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={},
            model="fixture",
            draft={"facebook": "Text", "instagram": "Text", "photo_brief": "Golf i kvällsljus"},
        )
        self.client.force_login(self.user)
        self.spec = compile_template("kinetic-text", {"headline": "Mer golf", "body": "Spela mer"})

    def url(self, name, **kwargs):
        return reverse("engine:" + name, kwargs={"workspace_id": self.company.pk, **kwargs})

    def project(self, run=None):
        return service.create_project(
            self.company, self.user, title="Mer golf", spec=self.spec, key=str(uuid.uuid4()), run=run
        )

    def test_motion_is_discoverable_from_media_and_draft(self):
        self.assertContains(self.client.get(self.url("media_library")), "Skapa motionvideo")
        self.assertContains(self.client.get(self.url("review", run_id=self.run.pk)), "Skapa motionvideo")

    def test_create_from_draft_is_local_and_preserves_copy(self):
        response = self.client.post(
            self.url("motion_list"),
            {
                "template_id": "kinetic-text",
                "title": "Mer golf",
                "headline": "Mer golf",
                "body": "Spela mer",
                "aspect_ratio": "9:16",
                "run_id": self.run.pk,
                "key": "create-ui-project-1",
            },
        )
        project = MotionProject.objects.get()
        self.assertRedirects(response, self.url("motion_workspace", project_id=project.pk))
        self.assertEqual(project.run_id, self.run.pk)
        self.run.refresh_from_db()
        self.assertEqual(self.run.draft["instagram"], "Text")
        self.assertFalse(MediaGeneration.objects.exists())
        response = self.client.get(self.url("motion_list") + "?run_id=" + str(self.run.pk))
        self.assertRedirects(response, self.url("motion_workspace", project_id=project.pk))

    def test_foreign_or_sent_draft_rejected(self):
        foreign = ContentRun.objects.create(workspace=self.other, context={}, model="fixture")
        for run in [foreign, self.run]:
            if run.pk == self.run.pk:
                run.delivery_status = "sent"
                run.save()
            self.assertEqual(self.client.get(self.url("motion_list") + "?run_id=" + str(run.pk)).status_code, 404)
            with self.assertRaises(ValueError):
                self.project(run=run)
        self.assertFalse(MotionProject.objects.exists())

    def test_invalid_fields_retained_and_numbers_not_invented(self):
        response = self.client.post(
            self.url("motion_list"),
            {
                "template_id": "monthly-wrapped",
                "title": "September",
                "aspect_ratio": "9:16",
                "month": "September",
                "key": "invalid-ui-project",
            },
        )
        self.assertContains(response, 'value="September"')
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(MotionProject.objects.exists())

    def test_edit_version_and_stale_form_protected(self):
        project = self.project()
        payload = {
            "action": "save",
            "revision": 1,
            "key": "save-ui-project-1",
            "title": project.title,
            "aspect_ratio": "1:1",
            "headline": "Ny rubrik",
            "body": "Spela mer",
        }
        response = self.client.post(self.url("motion_action", project_id=project.pk), payload)
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.current_revision, 2)
        payload["key"] = "save-ui-project-2"
        self.assertEqual(self.client.post(self.url("motion_action", project_id=project.pk), payload).status_code, 400)
        self.assertEqual(project.revisions.count(), 2)

    @patch.dict("os.environ", {"MOTION_WORKER_URL": "http://127.0.0.1:8778", "MOTION_WORKER_TOKEN": "t" * 32})
    def test_preview_queue_status_cancel_and_final_gate(self):
        project = self.project()
        url = self.url("motion_action", project_id=project.pk)
        self.client.post(url, {"action": "final", "revision": 1, "key": "final-ui-project"})
        self.assertFalse(MediaGeneration.objects.exists())
        self.client.post(url, {"action": "preview", "revision": 1, "key": "preview-ui-project"})
        job = project.revisions.get().renders.get()
        response = self.client.get(self.url("motion_status", project_id=project.pk))
        self.assertContains(response, "Väntar på rendering")
        self.assertContains(response, 'hx-trigger="every 3s"')
        self.client.post(url, {"action": "cancel", "revision": 1, "render_id": job.pk})
        job.generation.refresh_from_db()
        self.assertEqual(job.generation.status, "canceled")
        self.assertNotContains(
            self.client.get(self.url("motion_status", project_id=project.pk)), 'hx-trigger="every 3s"'
        )

    def test_company_isolation_for_workspace_and_status(self):
        project = service.create_project(
            self.other,
            self.other.owner,
            title="Other",
            spec=compile_template("kinetic-text", {"headline": "Other", "body": "Other"}, brand_id="workspace"),
            key="other-ui-project",
        )
        for route in ["motion_workspace", "motion_status"]:
            self.assertEqual(self.client.get(self.url(route, project_id=project.pk)).status_code, 404)

    def asset(self, **kwargs):
        return MediaAsset.objects.create(
            company=self.company,
            storage_key="fixture",
            mime_type="video/mp4",
            byte_size=10,
            sha256="a" * 64,
            kind="video",
            **kwargs,
        )

    def test_preview_excluded_from_library_picker_mcp_and_direct_selection(self):
        project = self.project()
        job = service.queue_render(
            self.company, self.user, project.pk, mode="preview", expected_revision=1, key="preview-asset-test"
        )
        asset = self.asset(alt_text="PREVIEW_ONLY")
        job.output_asset = asset
        job.save()
        storyboard = self.asset(alt_text="STORYBOARD_ONLY")
        MotionKeyframe.objects.create(render=job, asset=storyboard, scene_id="beat-01", frame=30)
        for response in [
            self.client.get(self.url("media_library")),
            self.client.get(self.url("media", run_id=self.run.pk)),
        ]:
            self.assertNotContains(response, "PREVIEW_ONLY")
            self.assertNotContains(response, "STORYBOARD_ONLY")
        self.assertNotIn(str(asset.pk), [item["id"] for item in media_options(self.run)])
        with self.assertRaises(MediaError):
            select_asset(self.run, asset)
        with self.assertRaises(OperatorError):
            select_run_asset(self.run, asset)
        with self.assertRaises(MediaError):
            select_asset(self.run, storyboard)

    def test_shared_mcp_library_contains_reusable_upload_and_final_excludes_expired(self):
        reusable = self.asset(alt_text="Reusable")
        self.asset(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual([item["id"] for item in media_options(self.run)], [str(reusable.pk)])

    def test_internal_media_runs_do_not_pollute_content_home(self):
        project = self.project()
        for model in ["creative-studio", "sequence-anchor-chain", "sequence-anchor-generation", "sequence-transition-bridge"]:
            ContentRun.objects.create(
                workspace=self.company,
                context={"media_only": True},
                model=model,
                draft={"photo_brief": "Internal media run"},
            )
        runs = self.client.get(self.url("home")).context["runs"]
        self.assertEqual([run.pk for run in runs], [self.run.pk])
        project.run.draft["instagram"] = "Mer golf med Golfkuponger"
        project.run.save(update_fields=["draft"])
        runs = self.client.get(self.url("home")).context["runs"]
        self.assertEqual([run.pk for run in runs], [project.run_id, self.run.pk])

    def test_sequence_carries_content_brief(self):
        response = self.client.get(self.url("sequence_list") + "?run_id=" + str(self.run.pk))
        self.assertContains(response, "Golf i kvällsljus")

    def test_standalone_motion_captures_facts_for_safe_delivery(self):
        from engine.delivery import _validate_context

        project = self.project()
        _validate_context(project.run)
        for key in ["profile", "voice", "current", "source"]:
            self.assertEqual(project.run.context[key], getattr(self.company, key))
        self.company.current = "Ändrat erbjudande"
        self.company.save(update_fields=["current"])
        project.run.workspace.refresh_from_db()
        with self.assertRaises(OperatorError):
            _validate_context(project.run)

    def test_web_delivery_checks_legacy_context_and_preview_before_network(self):
        from engine.forms import snapshot_company_context

        payload = {"action": "send", "facebook": "Text", "instagram": "Text", "reviewed": "on"}
        with patch("engine.postiz.request") as postiz:
            response = self.client.post(self.url("review", run_id=self.run.pk), payload)
            self.assertContains(response, "Underlaget har ändrats eller gått ut")
            project = self.project()
            job = service.queue_render(
                self.company, self.user, project.pk, mode="preview", expected_revision=1, key="delivery-preview-1"
            )
            job.output_asset = self.asset()
            job.save()
            self.run.context = snapshot_company_context(self.company)
            self.run.media_asset = job.output_asset
            self.run.save(update_fields=["context", "media_asset"])
            response = self.client.post(self.url("review", run_id=self.run.pk), payload)
            self.assertContains(response, "Godkänn Motion-förhandsvisningen")
            self.run.media_asset = None
            self.run.save(update_fields=["media_asset"])
            self.company.voice = "Ny tonalitet"
            self.company.save(update_fields=["voice"])
            response = self.client.post(self.url("review", run_id=self.run.pk), payload)
            self.assertContains(response, "Underlaget har ändrats eller gått ut")
            postiz.assert_not_called()

    def test_creative_copy_becomes_findable_with_the_same_company_snapshot(self):
        run_id = uuid.uuid4()
        self.client.post(self.url("media_new"), {"token": run_id})
        run = ContentRun.objects.get(pk=run_id)
        self.assertEqual(run.context["source"], self.company.source)
        self.assertEqual(run.context["valid_until"], self.company.valid_until.isoformat())
        self.client.post(
            self.url("review", run_id=run.pk), {"action": "save", "facebook": "Text", "instagram": "Text"}
        )
        runs = self.client.get(self.url("home")).context["runs"]
        self.assertIn(run.pk, [item.pk for item in runs])

    def test_malformed_draft_links_and_missing_revision_are_safe(self):
        for route in ["motion_list", "sequence_list"]:
            self.assertEqual(self.client.get(self.url(route) + "?run_id=invalid").status_code, 404)
        project = self.project()
        response = self.client.post(self.url("motion_action", project_id=project.pk), {"action": "preview"})
        self.assertRedirects(response, self.url("motion_workspace", project_id=project.pk))
        self.assertFalse(MediaGeneration.objects.exists())

    def test_custom_mcp_scenes_survive_web_editor(self):
        self.spec["scenes"][0]["duration_frames"] += 30
        project = self.project()
        response = self.client.get(self.url("motion_workspace", project_id=project.pk))
        self.assertContains(response, "Projektet har anpassade scener")
        self.assertNotContains(response, "Spara ny version")
        self.client.post(
            self.url("motion_action", project_id=project.pk),
            {
                "action": "save",
                "revision": 1,
                "key": "custom-edit",
                "title": "Mer golf",
                "aspect_ratio": "9:16",
                "headline": "Changed",
            },
        )
        project.refresh_from_db()
        self.assertEqual(project.current_revision, 1)
        self.assertEqual(project.revisions.get().spec, self.spec)

    def test_mcp_motion_tools_use_shared_services_and_authenticated_scope(self):
        from types import SimpleNamespace

        from asgiref.sync import async_to_sync

        from engine import mcp_server

        tools = {tool.name: tool for tool in async_to_sync(mcp_server.mcp.list_tools)()}
        names = {
            "list_motion_templates",
            "list_motion_projects",
            "create_motion_project",
            "get_motion_project",
            "update_motion_project",
            "render_motion_project",
            "approve_motion_preview",
            "cancel_motion_render",
        }
        self.assertTrue(names <= tools.keys())
        self.assertIn("run_id", tools["create_motion_project"].input_schema["properties"])
        self.assertTrue(tools["get_motion_project"].annotations.read_only_hint)

        def registered(name):
            return mcp_server.mcp._tool_manager.get_tool(name).fn

        token = SimpleNamespace(claims={"django_user_id": self.user.pk})
        with (
            patch("engine.mcp_auth.get_access_token", return_value=token),
            patch("engine.motion.mcp.service.create_project", wraps=service.create_project) as create,
        ):
            data = registered("create_motion_project")(
                str(self.company.pk),
                "MCP motion",
                "kinetic-text",
                {"headline": "Mer golf", "body": "Spela mer"},
                "mcp-motion-project-1",
                run_id=str(self.run.pk),
            )
            self.assertEqual(data["run_id"], str(self.run.pk))
            self.assertTrue(create.called)
            with self.assertRaises(mcp_server.ToolError):
                registered("render_motion_project")(
                    str(self.company.pk), data["project_id"], "final", 1, "mcp-final-render-1"
                )
            render = registered("render_motion_project")(
                str(self.company.pk), data["project_id"], "preview", 1, "mcp-preview-render-1"
            )
            canceled = registered("cancel_motion_render")(str(self.company.pk), render["render_id"])
            self.assertEqual(canceled["status"], "canceled")
            with self.assertRaises(mcp_server.ToolError):
                registered("list_motion_projects")(str(self.other.pk))
