"""Bearer-token verification for Content Engine's self-hosted MCP OAuth server."""

from __future__ import annotations

import hashlib
import os

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken as MCPAccessToken, TokenVerifier
from oauth2_provider.models import AccessToken as OAuthAccessToken

from .operator import OperatorError


class ContentEngineTokenVerifier(TokenVerifier):
    """Verify opaque OAuth access tokens issued by this Content Engine deployment."""

    def __init__(self) -> None:
        self.allow_local = os.environ.get("MCP_ALLOW_INSECURE_LOCAL", "").lower() in {"1", "true", "yes"}
        self.dev_token = os.environ.get("MCP_DEV_BEARER_TOKEN", "") if self.allow_local else ""
        self.dev_email = os.environ.get("MCP_DEV_USER_EMAIL", "") if self.allow_local else ""
        self.required_scope = os.environ.get(
            "MCP_REQUIRED_SCOPE", getattr(settings, "MCP_REQUIRED_SCOPE", "content-engine.operate")
        ).strip() or "content-engine.operate"
        self.resource = os.environ.get("MCP_RESOURCE_URL", getattr(settings, "MCP_RESOURCE_URL", "")).strip().rstrip("/")
        if not self.resource and not self.dev_token:
            raise RuntimeError("MCP_RESOURCE_URL is required for OAuth token audience validation")

    @sync_to_async(thread_sensitive=True)
    def _lookup(self, raw_token: str):
        checksum = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        token = (
            OAuthAccessToken.objects.select_related("user", "application")
            .filter(token_checksum=checksum, expires__gt=timezone.now())
            .first()
        )
        if not token or not token.user_id or not token.user.is_active or not token.application_id:
            return None
        if self.required_scope and not token.allow_scopes([self.required_scope]):
            return None
        # Require RFC 8707 audience binding. An unrestricted token is deliberately not accepted by MCP.
        if not token.resource or not token.allows_audience(self.resource):
            return None
        return token

    async def verify_token(self, token: str) -> MCPAccessToken | None:
        if self.dev_token and token == self.dev_token:
            if not self.dev_email:
                return None
            return MCPAccessToken(
                token=token,
                client_id="local-dev",
                scopes=[self.required_scope],
                subject=self.dev_email.lower(),
                resource=self.resource or None,
                claims={"content_engine_user": self.dev_email.lower()},
            )
        access = await self._lookup(token)
        if not access:
            return None
        return MCPAccessToken(
            token=token,
            client_id=access.application.client_id,
            scopes=list(access.scopes.keys()),
            expires_at=int(access.expires.timestamp()),
            subject=str(access.user_id),
            resource=self.resource,
            claims={"django_user_id": access.user_id},
        )


def current_django_user():
    token = get_access_token()
    if token is None:
        raise OperatorError("MCP-anropet saknar autentiserad användare.")
    claims = token.claims or {}
    user_id = claims.get("django_user_id")
    User = get_user_model()
    if user_id is not None:
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user:
            return user
        raise OperatorError("OAuth-token är inte kopplad till en aktiv Content Engine-användare.")

    # Local development only: preserve the explicit email mapping used by CI/manual smoke tests.
    identity = str(claims.get("content_engine_user") or "").strip().lower()
    if not identity:
        raise OperatorError("Access token saknar Content Engine-användaridentitet.")
    users = list(User.objects.filter(email__iexact=identity, is_active=True)[:2])
    if len(users) != 1:
        users = list(User.objects.filter(username__iexact=identity, is_active=True)[:2])
    if len(users) != 1:
        raise OperatorError("Den autentiserade identiteten är inte entydigt kopplad till en aktiv Content Engine-användare.")
    return users[0]


# Backwards-compatible symbol for the already-tested MCP tool module. The implementation
# is no longer OIDC/JWT based; production tokens are issued and verified by Content Engine itself.
OIDCTokenVerifier = ContentEngineTokenVerifier
