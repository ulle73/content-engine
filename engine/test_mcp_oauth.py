import json
import os
from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, set_token_value

from .mcp_auth import ContentEngineTokenVerifier
from .mcp_settings import OAUTH2_PROVIDER as MCP_OAUTH_SETTINGS


@override_settings(ROOT_URLCONF="engine.mcp_auth_urls", OAUTH2_PROVIDER=MCP_OAUTH_SETTINGS)
class SelfHostedMCPOAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operator@example.com",
            email="operator@example.com",
            password="test-only-strong-password-3901",
        )

    def test_authorization_metadata_advertises_self_hosted_mcp_oauth(self):
        response = self.client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["issuer"], "http://127.0.0.1:8765")
        self.assertTrue(payload["authorization_endpoint"].endswith("/oauth/authorize/"))
        self.assertTrue(payload["token_endpoint"].endswith("/oauth/token/"))
        self.assertTrue(payload["registration_endpoint"].endswith("/oauth/register/"))
        self.assertIn("authorization_code", payload["grant_types_supported"])
        self.assertNotIn("implicit", payload["grant_types_supported"])
        self.assertIn("S256", payload["code_challenge_methods_supported"])
        self.assertIn("content-engine.operate", payload["scopes_supported"])

    def test_dcr_accepts_only_explicit_chatgpt_callback_hosts(self):
        allowed = {
            "client_name": "ChatGPT Content Engine",
            "redirect_uris": ["https://chatgpt.com/connector/oauth/content-engine-test"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }
        response = self.client.post("/oauth/register/", data=json.dumps(allowed), content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["redirect_uris"], allowed["redirect_uris"])

        blocked = {**allowed, "redirect_uris": ["https://attacker.example/callback"]}
        response = self.client.post("/oauth/register/", data=json.dumps(blocked), content_type="application/json")
        self.assertIn(response.status_code, {401, 403})

    def test_self_issued_token_is_scope_and_resource_bound(self):
        app = Application.objects.create(
            name="ChatGPT Content Engine",
            user=self.user,
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            redirect_uris="https://chatgpt.com/connector/oauth/content-engine-test",
        )
        raw = "test-self-issued-access-token"
        token = AccessToken(
            user=self.user,
            application=app,
            expires=timezone.now() + timedelta(hours=1),
            scope="content-engine.operate offline_access",
            resource=["http://127.0.0.1:8766/mcp"],
        )
        set_token_value(token, raw)
        token.save()

        with patch.dict(os.environ, {"MCP_RESOURCE_URL": "http://127.0.0.1:8766/mcp", "MCP_REQUIRED_SCOPE": "content-engine.operate"}):
            verified = async_to_sync(ContentEngineTokenVerifier().verify_token)(raw)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.claims["django_user_id"], self.user.pk)

        with patch.dict(os.environ, {"MCP_RESOURCE_URL": "http://127.0.0.1:8766/other", "MCP_REQUIRED_SCOPE": "content-engine.operate"}):
            self.assertIsNone(async_to_sync(ContentEngineTokenVerifier().verify_token)(raw))
