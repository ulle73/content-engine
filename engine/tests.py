import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Company, ContentRun
from .postiz import make_payload


class SourceQuoteTests(TestCase):
    @patch("engine.generation.structured_analysis")
    def test_draft_writer_receives_editorial_brief_without_ranking_metadata(self, structured):
        from .generation import generate

        parsed = Mock()
        parsed.model_dump.return_value = DRAFT
        structured.return_value = (
            parsed,
            {"provider": "openrouter", "service": "text", "model": "free-test", "usage": {}, "cost_usd": 0},
        )
        generate(
            {"profile": "Golf", "competitor_signals": [{"id": "7", "score": 81}]},
            idea={
                "title": "Egen vinkel",
                "angle": "Analysera beslut",
                "photo_brief": "Eget foto",
                "ranking": {"score": 81},
                "signal_id": "7",
            },
        )
        payload = structured.call_args.kwargs["payload"]
        self.assertNotIn("competitor_signals", payload["company_context"])
        self.assertEqual(set(payload["selected_idea"]), {"title", "angle", "photo_brief"})
        self.assertEqual(structured.call_args.kwargs["operation"], "draft")

    @patch("engine.generation.structured_analysis")
    def test_quotes_accept_only_exact_current_or_profile_text(self, structured):
        from copy import deepcopy

        from .generation import generate

        context = {
            "current": "Nya rangebollar.",
            "profile": "Vi hjälper amatörgolfare.",
            "voice": "Garanterat tio slag bättre.",
        }

        def response_for(item, index):
            parsed = Mock()
            parsed.model_dump.return_value = item
            return (
                parsed,
                {
                    "provider": "openrouter",
                    "service": "text",
                    "model": "free-test",
                    "response_id": f"resp-{index}",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30, "cost": 0},
                    "cost_usd": 0,
                },
            )

        ideas = deepcopy(IDEAS["ideas"])
        ideas[1]["source_quote"] = context["profile"]
        structured.side_effect = [response_for(item, index) for index, item in enumerate(ideas, start=1)]
        result = generate(context)
        self.assertEqual(result["ideas"][0]["source_field"], "current")
        self.assertEqual(result["ideas"][1]["source_field"], "profile")
        self.assertEqual(context["_provider_usage_ideas"]["provider"], "openrouter")
        self.assertEqual(context["_provider_usage_ideas"]["calls"], 3)
        self.assertEqual(context["_provider_usage_ideas"]["usage"]["total_tokens"], 90)
        self.assertEqual(
            [call.kwargs["operation"] for call in structured.call_args_list],
            ["idea_1", "idea_2", "idea_3"],
        )
        self.assertTrue(all(call.kwargs["max_tokens"] == 1000 for call in structured.call_args_list))
        self.assertEqual(structured.call_args_list[1].kwargs["payload"]["variation"]["avoid_titles"], ["Idé 0"])

        for invalid in (context["voice"], "Vi hjälper alla golfare.", ""):
            invalid_ideas = deepcopy(IDEAS["ideas"])
            invalid_ideas[1]["source_quote"] = invalid
            structured.side_effect = [
                response_for(item, index) for index, item in enumerate(invalid_ideas, start=1)
            ]
            with self.assertRaisesRegex(ValueError, "källcitat"):
                generate(context)


@override_settings(LOCAL_HTTP=True)
class FirstRunTests(TestCase):
    def fields(self):
        return {
            "username": "owner@example.test",
            "company": "Mitt företag",
            "password1": "Strong-test-passphrase-291!",
            "password2": "Strong-test-passphrase-291!",
        }

    def test_first_visit_creates_admin_and_company_and_closes_registration(self):
        self.assertRedirects(self.client.get("/"), "/accounts/login/?next=/", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/accounts/login/"), "/setup/")
        self.assertContains(self.client.get("/setup/"), "Skapa första administratören")
        self.assertRedirects(self.client.post("/setup/", self.fields()), "/")
        user = get_user_model().objects.get()
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(self.fields()["password1"]))
        self.assertEqual(Company.objects.get().owner, user)
        self.client.logout()
        self.assertRedirects(self.client.post("/setup/", self.fields()), "/accounts/login/")
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertRedirects(
            self.client.post(
                "/accounts/login/", {"username": "OWNER@example.test", "password": self.fields()["password1"]}
            ),
            "/",
        )

    @override_settings(LOCAL_HTTP=False, SETUP_TOKEN="test-installation-secret")
    def test_public_setup_requires_installation_secret(self):
        fields = self.fields()
        self.assertEqual(self.client.post("/setup/", fields).status_code, 200)
        self.assertFalse(get_user_model().objects.exists())
        fields["setup_token"] = "wrong"
        self.client.post("/setup/", fields)
        self.assertFalse(get_user_model().objects.exists())
        fields["setup_token"] = "test-installation-secret"
        self.assertRedirects(self.client.post("/setup/", fields), "/")

    def test_setup_enforces_csrf_and_password_validation(self):
        from django.test import Client

        self.assertEqual(Client(enforce_csrf_checks=True).post("/setup/", self.fields()).status_code, 403)
        fields = {**self.fields(), "password1": "123", "password2": "123"}
        self.client.post("/setup/", fields)
        self.assertFalse(get_user_model().objects.exists())


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
        self.user = get_user_model().objects.create_user(username="editor@example.test", password="test-only-password")
        self.workspace = self.context = Company.objects.create(
            owner=self.user,
            name="Testföretag",
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
        outsider = get_user_model().objects.create_user(username="outsider@example.test")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(self.url("home")).status_code, 404)
        self.assertEqual(self.client.post(self.url("ideas")).status_code, 404)

    @patch("engine.views.generate")
    def test_ideas_draft_and_repeat_do_not_publish_or_duplicate(self, generate):
        generate.side_effect = [IDEAS, DRAFT]
        self.client.post(self.url("ideas"))
        run = ContentRun.objects.get(workspace=self.workspace)
        response = self.client.post(self.url("draft", run_id=run.pk, idea_index=0))
        self.assertEqual(response.status_code, 302)
        run.refresh_from_db()
        self.assertEqual(run.draft, DRAFT)
        self.assertEqual(run.delivery_status, "draft")
        self.assertEqual(self.client.get(self.url("review", run_id=run.pk)).status_code, 200)
        self.client.post(self.url("draft", run_id=run.pk, idea_index=0))
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(list(run.events.values_list("action", flat=True)), ["ranked", "selected", "draft_created"])
        from .signals import RANKER_VERSION

        self.assertEqual(run.events.get(action="ranked").data["ranker_version"], RANKER_VERSION)
        self.client.post(self.url("reject_idea", run_id=run.pk, idea_index=1))
        self.assertEqual(run.events.get(action="rejected").idea_index, 1)

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
        )

    @patch("engine.postiz.request")
    def test_send_requires_review_and_does_not_repeat(self, request):
        run = self.saved_draft()
        url = self.url("review", run_id=run.pk)
        fields = {"facebook": "FB", "instagram": "IG", "channels": ["fb-1"], "action": "send"}
        self.client.post(url, fields)
        request.assert_not_called()
        self.assertFalse(run.events.filter(action="approved").exists())
        edit = run.events.get(action="edited")
        self.assertEqual(edit.data["before"]["facebook"], "Nya rangebollar.")
        self.assertEqual(edit.data["after"]["facebook"], "FB")
        request.return_value = [{"postId": "external-id", "integration": "fb-1"}]
        fields["reviewed"] = "on"
        self.client.post(url, fields)
        run.refresh_from_db()
        self.assertEqual(run.delivery_status, "sent")
        self.assertEqual(request.call_args.kwargs["json"]["type"], "draft")
        self.client.post(url, fields)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(run.events.filter(action="approved").count(), 1)
        self.assertEqual(run.events.get(action="postiz_draft").data["posts"][0]["postId"], "external-id")
        self.assertFalse(run.events.filter(action="published").exists())

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
