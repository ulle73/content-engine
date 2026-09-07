from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BrandContext, ContentRun
from .postiz import make_payload

IDEAS = {
    "ideas": [
        {
            "title": f"Idé {i}",
            "angle": "Aktuell nyhet",
            "reason": "Egen källa",
            "source_quote": "Nya rangebollar.",
            "photo_brief": "Fotografera rangebollarna.",
        }
        for i in range(3)
    ]
}
DRAFT = {
    "facebook": "Nya rangebollar.",
    "instagram": "Nya rangebollar på rangen.",
    "photo_brief": "Använd en egen bild.",
    "checks": ["Kontrollera uppgiften."],
}


class ContentFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="editor@example.test", password="test-only-password")
        self.workspace = self.user.workspace_memberships.first().workspace
        self.context = BrandContext.objects.create(
            workspace=self.workspace,
            profile="Testföretag.",
            voice="Kort och vänligt.",
            current="Nya rangebollar.",
            source="Ansvarig",
            valid_until=timezone.localdate() + timedelta(days=3),
        )
        self.client.force_login(self.user)

    def url(self, name, **kwargs):
        return reverse(f"engine:{name}", kwargs={"workspace_id": self.workspace.pk, **kwargs})

    def test_real_pages_and_workspace_isolation(self):
        self.assertEqual(self.client.get(self.url("home")).status_code, 200)
        self.assertEqual(self.client.get(self.url("connect")).status_code, 200)
        outsider = get_user_model().objects.create_user(email="outsider@example.test")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(self.url("home")).status_code, 403)
        self.assertEqual(self.client.post(self.url("ideas")).status_code, 403)

    @patch("engine.views.generate")
    def test_ideas_draft_and_repeat_do_not_publish_or_duplicate(self, generate):
        generate.side_effect = [IDEAS, DRAFT]
        self.client.post(self.url("ideas"))
        run = ContentRun.objects.get(workspace=self.workspace)
        response = self.client.post(self.url("draft", run_id=run.pk, idea_index=0))
        self.assertEqual(response.status_code, 302)
        run.refresh_from_db()
        self.assertIsNotNone(run.post_id)
        self.assertIsNone(run.post.scheduled_at)
        self.assertEqual(run.post.platform_posts.count(), 0)
        self.assertEqual(self.client.get(self.url("review", run_id=run.pk)).status_code, 200)
        self.client.post(self.url("draft", run_id=run.pk, idea_index=0))
        self.assertEqual(generate.call_count, 2)

    @patch("engine.views.generate")
    def test_expired_context_never_calls_ai(self, generate):
        self.context.valid_until = timezone.localdate() - timedelta(days=1)
        self.context.save()
        self.client.post(self.url("ideas"))
        generate.assert_not_called()
        self.assertFalse(ContentRun.objects.exists())

    def test_postiz_contract_is_draft_and_platform_specific(self):
        payload = make_payload(
            [{"id": "fb-1", "identifier": "facebook"}, {"id": "ig-1", "identifier": "instagram"}],
            "Facebooktext",
            "Instagramtext",
            [{"id": "image-1", "path": "https://example.test/photo.jpg"}],
        )
        self.assertEqual(payload["type"], "draft")
        self.assertEqual(payload["posts"][1]["value"][0]["content"], "Instagramtext")
        self.assertEqual(payload["posts"][1]["settings"], {"__type": "instagram", "post_type": "post"})

    def saved_draft(self):
        from apps.composer.models import Post

        self.context.postiz_key = "test-only-key"
        self.context.postiz_channels = [{"id": "fb-1", "name": "Test FB", "identifier": "facebook"}]
        self.context.save()
        return ContentRun.objects.create(
            workspace=self.workspace,
            author=self.user,
            model="test",
            context={
                "current": self.context.current,
                "source": self.context.source,
                "profile": self.context.profile,
                "valid_until": self.context.valid_until.isoformat(),
            },
            draft=DRAFT,
            post=Post.objects.create(workspace=self.workspace, author=self.user, caption="Test"),
        )

    @patch("engine.postiz.request")
    def test_send_requires_review_and_does_not_repeat(self, request):
        run = self.saved_draft()
        url = self.url("review", run_id=run.pk)
        fields = {"facebook": "FB", "instagram": "IG", "channels": ["fb-1"], "action": "send"}
        self.client.post(url, fields)
        request.assert_not_called()
        request.return_value = [{"postId": "external-id", "integration": "fb-1"}]
        fields["reviewed"] = "on"
        self.client.post(url, fields)
        run.refresh_from_db()
        self.assertEqual(run.delivery_status, "sent")
        self.assertEqual(request.call_args.kwargs["json"]["type"], "draft")
        self.client.post(url, fields)
        self.assertEqual(request.call_count, 1)

    @patch("engine.postiz.request")
    def test_uncertain_transfer_needs_explicit_recovery(self, request):
        from engine.postiz import PostizError

        run = self.saved_draft()
        url = self.url("review", run_id=run.pk)
        request.side_effect = PostizError("timeout")
        fields = {"facebook": "FB", "instagram": "IG", "channels": ["fb-1"], "action": "send", "reviewed": "on"}
        self.client.post(url, fields)
        run.refresh_from_db()
        self.assertEqual(run.delivery_status, "unknown")
        self.client.post(url, fields)
        self.assertEqual(request.call_count, 1)
        self.client.post(url, {"action": "reset", "checked_postiz": "on"})
        run.refresh_from_db()
        self.assertEqual(run.delivery_status, "draft")
