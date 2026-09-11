import base64
import io
from datetime import timedelta, timezone as dt_timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from engine.delivery import deliver_to_postiz, reset_unknown_delivery
from engine.operator import (
    UnknownExternalState,
    company_summary,
    ingest_image_once,
    resolve_company,
    serialize_run,
    update_copy,
)
from engine.own_performance import matching_run
from engine.models import Company, ContentRun
from engine.postiz import PostizError, make_payload
from operator_bridge.models import OperatorAction, RunState


def picture():
    output = io.BytesIO()
    Image.new("RGB", (64, 96), "green").save(output, "PNG")
    return output.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class OperatorBridgeTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.user = get_user_model().objects.create_user(
            username="operator@example.com", email="operator@example.com"
        )
        self.other_user = get_user_model().objects.create_user(
            username="other@example.com", email="other@example.com"
        )
        self.company = Company.objects.create(
            owner=self.user,
            name="Sänk Dig Golf",
            profile="Sänk Dig Golf hjälper svenska golfare att utvecklas.",
            voice="Tydlig, kunnig och varm.",
            current="Vi publicerar träningsinnehåll den här veckan.",
            source="Internt verifierat underlag",
            valid_until=timezone.localdate() + timedelta(days=7),
            postiz_channels=[{"id": "fb", "name": "Facebook", "identifier": "facebook"}],
        )
        self.company.postiz_key = "postiz-test-only"
        self.company.save()
        self.other_company = Company.objects.create(owner=self.other_user, name="Annat bolag")
        self.run = ContentRun.objects.create(
            workspace=self.company,
            author=self.user,
            context={
                "company": self.company.name,
                "channel": "organic",
                "profile": self.company.profile,
                "voice": self.company.voice,
                "current": self.company.current,
                "source": self.company.source,
                "valid_until": self.company.valid_until.isoformat(),
                "captured_at": timezone.now().isoformat(),
                "competitor_signals": [],
                "recent_posts": [],
            },
            ideas=[
                {
                    "title": "Bättre närspel",
                    "angle": "Ett konkret träningstips",
                    "photo_brief": "Golfare på övningsgreen",
                    "signal_id": "",
                    "profile_relevance": 3,
                    "current_relevance": 3,
                }
            ],
            selected=0,
            draft={"facebook": "Facebooktext", "instagram": "Instagramtext", "photo_brief": "Övningsgreen"},
            model="test",
            channel="organic",
        )
        RunState.objects.create(run=self.run)

    def test_company_scope_and_secret_redaction(self):
        self.assertEqual(resolve_company(self.user, str(self.company.pk)), self.company)
        self.assertEqual(resolve_company(self.user, "Sänk Dig Golf"), self.company)
        with self.assertRaises(ValueError):
            resolve_company(self.user, str(self.other_company.pk))
        summary = company_summary(self.company)
        self.assertTrue(summary["postiz_connected"])
        self.assertNotIn("postiz_key", summary)
        self.assertNotIn("postiz_ciphertext", summary)
        self.assertNotIn("postiz-test-only", str(summary))

    def test_chatgpt_image_ingest_is_persisted_deduped_and_selected(self):
        encoded = base64.b64encode(picture()).decode()
        asset, updated = ingest_image_once(
            self.run,
            self.user,
            image_base64=encoded,
            brief="ChatGPT-genererad golfbild",
            alt_text="Golfare på green",
            select=True,
            expected_revision=0,
            idempotency_key="chatgpt-image-0001",
        )
        updated.refresh_from_db()
        self.assertEqual(updated.media_asset_id, asset.pk)
        self.assertEqual(asset.origin, "generated")
        self.assertEqual(asset.provider, "chatgpt")
        self.assertEqual(asset.operator_provenance.source, "chatgpt")
        self.assertEqual(RunState.objects.get(run=self.run).revision, 1)
        self.assertTrue(self.run.events.filter(action="media_ingested").exists())
        self.assertTrue(self.run.events.filter(action="media_selected").exists())
        again, _ = ingest_image_once(
            self.run,
            self.user,
            image_base64=encoded,
            brief="ChatGPT-genererad golfbild",
            alt_text="Golfare på green",
            select=True,
            expected_revision=0,
            idempotency_key="chatgpt-image-0001",
        )
        self.assertEqual(again.pk, asset.pk)
        self.assertEqual(OperatorAction.objects.filter(company=self.company, key="chatgpt-image-0001").count(), 1)

    @patch("engine.delivery.postiz_request")
    def test_schedule_is_exactly_once_and_keeps_performance_mapping(self, postiz_request):
        postiz_request.return_value = [{"postId": "post-123"}]
        scheduled = (timezone.localtime(timezone.now()) + timedelta(days=1)).replace(tzinfo=None, second=0, microsecond=0)
        delivered = deliver_to_postiz(
            self.run,
            self.user,
            mode="schedule",
            schedule_at=scheduled.isoformat(),
            expected_revision=0,
            idempotency_key="postiz-schedule-0001",
        )
        self.assertEqual(delivered.delivery_status, "sent")
        self.assertEqual(delivered.delivery_result[0]["integration"], "fb")
        self.assertEqual(delivered.delivery_result[0]["mode"], "schedule")
        self.assertEqual(matching_run(self.company, "post-123", "fb").pk, self.run.pk)
        sent_payload = postiz_request.call_args.kwargs["json"]
        self.assertEqual(sent_payload["type"], "schedule")
        self.assertTrue(sent_payload["date"].endswith("+00:00"))
        second = deliver_to_postiz(
            self.run,
            self.user,
            mode="schedule",
            schedule_at=scheduled.isoformat(),
            expected_revision=0,
            idempotency_key="postiz-schedule-0001",
        )
        self.assertEqual(second.pk, delivered.pk)
        self.assertEqual(postiz_request.call_count, 1)

    @patch("engine.delivery.postiz_request")
    def test_postiz_draft_can_be_superseded_by_later_schedule_without_breaking_ml_identity(self, postiz_request):
        calls = []

        def response(key, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if method == "POST" and path == "/posts" and len([c for c in calls if c[0] == "POST"]) == 1:
                return [{"postId": "draft-123"}]
            if method == "POST" and path == "/posts":
                return [{"postId": "scheduled-456"}]
            if method == "DELETE":
                return {"id": path.rsplit("/", 1)[-1]}
            raise AssertionError((method, path))

        postiz_request.side_effect = response
        draft = deliver_to_postiz(
            self.run, self.user, mode="draft", expected_revision=0, idempotency_key="postiz-draft-first-1"
        )
        self.assertEqual(draft.delivery_result[0]["postId"], "draft-123")
        revision = RunState.objects.get(run=self.run).revision
        scheduled_at = (timezone.localtime(timezone.now()) + timedelta(days=2)).replace(
            tzinfo=None, second=0, microsecond=0
        )
        scheduled = deliver_to_postiz(
            draft, self.user, mode="schedule", schedule_at=scheduled_at.isoformat(),
            expected_revision=revision, idempotency_key="postiz-supersede-0001"
        )
        self.assertEqual(scheduled.delivery_result[0]["postId"], "scheduled-456")
        self.assertIsNone(matching_run(self.company, "draft-123", "fb"))
        self.assertEqual(matching_run(self.company, "scheduled-456", "fb").pk, self.run.pk)
        self.assertIn(("DELETE", "/posts/draft-123"), [(m, p) for m, p, _ in calls])

    @patch("engine.delivery.postiz_request")
    def test_remote_postiz_draft_can_be_reopened_edited_and_replaced(self, postiz_request):
        created = []

        def response(key, method, path, **kwargs):
            if method == "POST" and path == "/posts":
                post_id = f"draft-{len(created) + 1}"
                created.append(post_id)
                return [{"postId": post_id}]
            if method == "DELETE":
                return {"id": path.rsplit("/", 1)[-1]}
            raise AssertionError((method, path))

        postiz_request.side_effect = response
        first = deliver_to_postiz(
            self.run, self.user, mode="draft", expected_revision=0, idempotency_key="draft-edit-first-1"
        )
        revision = RunState.objects.get(run=self.run).revision
        edited = update_copy(
            first, facebook="Mindre säljig Facebooktext", instagram="Mindre säljig Instagramtext",
            expected_revision=revision, reason="mindre säljig"
        )
        edited.refresh_from_db()
        self.assertEqual(edited.delivery_status, "draft")
        self.assertEqual(edited.delivery_result[0]["postId"], "draft-1")
        new_revision = RunState.objects.get(run=self.run).revision
        replaced = deliver_to_postiz(
            edited, self.user, mode="draft", expected_revision=new_revision, idempotency_key="draft-edit-replace-1"
        )
        self.assertEqual(replaced.delivery_result[0]["postId"], "draft-2")
        self.assertTrue(
            self.run.events.filter(action="postiz_draft_reopened").exists()
        )
        delete_paths = [call.args[2] for call in postiz_request.call_args_list if call.args[1] == "DELETE"]
        self.assertIn("/posts/draft-1", delete_paths)

    @patch("engine.delivery.postiz_request")
    def test_uncertain_postiz_write_blocks_replay_until_explicit_reconciliation(self, postiz_request):
        postiz_request.side_effect = PostizError("timeout", uncertain=True)
        with self.assertRaises(ValueError):
            deliver_to_postiz(
                self.run,
                self.user,
                mode="draft",
                expected_revision=0,
                idempotency_key="postiz-draft-unknown-1",
            )
        self.run.refresh_from_db()
        self.assertEqual(self.run.delivery_status, "unknown")
        with self.assertRaises(UnknownExternalState):
            deliver_to_postiz(
                self.run,
                self.user,
                mode="draft",
                expected_revision=0,
                idempotency_key="postiz-draft-unknown-1",
            )
        restored = reset_unknown_delivery(
            self.run,
            self.user,
            confirmed_no_post_exists=True,
            idempotency_key="reconcile-postiz-0001",
        )
        self.assertEqual(restored.delivery_status, "draft")

    def test_postiz_payload_has_explicit_modes(self):
        channels = [{"id": "fb", "name": "Facebook", "identifier": "facebook"}]
        self.assertEqual(make_payload(channels, "FB", "IG", [], mode="draft")["type"], "draft")
        self.assertEqual(make_payload(channels, "FB", "IG", [], mode="now")["type"], "now")
        scheduled = timezone.now() + timedelta(days=1)
        payload = make_payload(channels, "FB", "IG", [], mode="schedule", scheduled_for=scheduled)
        self.assertEqual(payload["type"], "schedule")
        self.assertEqual(payload["date"], scheduled.astimezone(dt_timezone.utc).isoformat())

    def test_serialized_run_exposes_revision_but_no_secret(self):
        payload = serialize_run(self.run)
        self.assertEqual(payload["revision"], 0)
        self.assertNotIn("postiz-test-only", str(payload))


class MCPImportTests(TestCase):
    def test_mcp_server_builds_in_local_test_mode(self):
        # CI config supplies MCP_ALLOW_INSECURE_LOCAL and the local bearer identity before import.
        from engine import mcp_server

        self.assertIsNotNone(mcp_server.app)
        self.assertTrue(hasattr(mcp_server, "create_postiz_draft"))
        self.assertTrue(hasattr(mcp_server, "schedule_postiz"))
        self.assertTrue(hasattr(mcp_server, "publish_postiz_now"))
