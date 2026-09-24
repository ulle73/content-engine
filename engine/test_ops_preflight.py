import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import Company, ContentRun, MediaAsset, MediaGeneration


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class D2HiggsfieldPreflightCommandTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media_root = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.media_root.enable()
        self.addCleanup(self.media_root.disable)
        self.user = get_user_model().objects.create_user(username="d2-preflight-owner")
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golfkuponger",
            current="Current",
            source="Owner",
        )

    @patch("engine.management.commands.d2_higgsfield_preflight.higgsfield_configured", return_value=False)
    def test_preflight_fails_closed_without_dedicated_gk_credential(self, configured):
        with self.assertRaisesRegex(CommandError, "HIGGSFIELD_API_KEY_GK"):
            call_command("d2_higgsfield_preflight", "--token", "d2-test")
        self.assertFalse(ContentRun.objects.filter(model="ops-d2-preflight").exists())
        self.assertEqual(MediaAsset.objects.count(), 0)
        self.assertEqual(MediaGeneration.objects.count(), 0)

    @patch("engine.management.commands.d2_higgsfield_preflight.higgsfield_configured", return_value=True)
    @patch("engine.management.commands.d2_higgsfield_preflight.preview_job")
    def test_preflight_stays_nonbillable_outputs_safe_metadata_and_cleans_up(self, preview, configured):
        def reviewed(job):
            job.usage = {"estimate": {"usd": "0.12", "credits": 3}}
            job.save(update_fields=["usage"])
            return job

        preview.side_effect = reviewed
        stdout = io.StringIO()
        call_command("d2_higgsfield_preflight", "--token", "d2-test", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("D2_PREFLIGHT_OK", output)
        self.assertIn('"status": "queued"', output)
        self.assertIn('"provider_id_present": false', output)
        self.assertIn('"recipe": "scroll_transition_bridge"', output)
        self.assertIn('"END_IMAGE"', output)
        self.assertIn('"START_IMAGE"', output)
        self.assertIn('"usd": "0.12"', output)
        self.assertNotIn("http", output.lower())
        self.assertEqual(preview.call_count, 1)
        job = preview.call_args.args[0]
        self.assertEqual(job.status, "queued")
        self.assertFalse(job.provider_id)

        self.assertFalse(ContentRun.objects.filter(model="ops-d2-preflight").exists())
        self.assertEqual(MediaAsset.objects.count(), 0)
        self.assertEqual(MediaGeneration.objects.count(), 0)
