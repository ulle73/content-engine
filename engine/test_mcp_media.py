import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from .mcp_operations import cancel_generation, list_recent_generations, serialize_generation
from .media import create_job, store_asset
from .creative_core import ReferenceRole
from .media_references import add_generation_reference
from .models import Company, ContentRun, MediaGeneration


class MCPMediaOperationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="mcp-media")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger", profile="Golf")
        self.run = ContentRun.objects.create(
            workspace=self.company, author=self.user, context={"profile": "Golf"}, ideas=[{"title": "Golf"}],
            selected=0, draft={"instagram": "Text"}, model="test",
        )

    def job(self, brief="Skapa en premium reel cirka 8 sekunder"):
        return create_job(self.run, token=uuid.uuid4(), kind="video", brief=brief)

    def test_safe_generation_diagnostics_expose_shared_engine_provenance(self):
        job = self.job()
        data = serialize_generation(job, diagnostics=True)
        self.assertEqual(data["job_id"], str(job.pk))
        self.assertEqual(data["status_message"], "Sparad och väntar på start.")
        self.assertEqual(data["diagnostics"]["original_request"], job.brief)
        self.assertIn("SCENE:", data["diagnostics"]["compiled_prompt"])
        self.assertEqual(data["diagnostics"]["structured_brief"]["duration_seconds"], 8)
        self.assertIn("registry_version", data["diagnostics"])
        self.assertNotIn("logo_sha256", data["diagnostics"]["parameters"])

    def test_safe_generation_diagnostics_include_canonical_references(self):
        from .test_media import picture
        job = self.job()
        reference = store_asset(self.company, picture())
        add_generation_reference(job, reference, ReferenceRole.style_reference)
        data = serialize_generation(job, diagnostics=True)
        self.assertEqual(data["diagnostics"]["references"][0]["role"], ReferenceRole.style_reference.value)
        self.assertEqual(data["diagnostics"]["references"][0]["asset_id"], str(reference.pk))
        self.assertNotIn("storage_key", data["diagnostics"]["references"][0])

    def test_recent_generations_are_company_scoped_and_bounded(self):
        own = self.job()
        outsider = get_user_model().objects.create_user(username="mcp-other")
        other_company = Company.objects.create(owner=outsider, name="Other")
        other_run = ContentRun.objects.create(workspace=other_company, author=outsider, context={}, ideas=[], draft={"instagram": "x"}, model="test")
        MediaGeneration.objects.create(run=other_run, kind="video", provider="higgsfield", brief="other", prompt="other")
        rows = list_recent_generations(self.company, limit=50)
        self.assertEqual([row["job_id"] for row in rows], [str(own.pk)])

    def test_cancel_generation_reuses_domain_cancel_and_is_idempotent(self):
        job = self.job()
        canceled = cancel_generation(job)
        self.assertEqual(canceled.status, "canceled")
        again = cancel_generation(canceled)
        self.assertEqual(again.status, "canceled")
