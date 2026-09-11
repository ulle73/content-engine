"""OIDC bearer-token verification for the Content Engine MCP resource server."""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

import httpx
import jwt
from django.contrib.auth import get_user_model
from django.db.models import Q
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier

from .operator import OperatorError


def _https_url(name: str, *, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if not value and not required:
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError(f"{name} must be an absolute https URL")
    return value.rstrip("/")


def _jwks_url(issuer: str) -> str:
    explicit = _https_url("MCP_AUTH_JWKS_URL", required=False)
    if explicit:
        return explicit
    if not issuer:
        return ""
    discovery_url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        response = httpx.get(discovery_url, timeout=10, follow_redirects=False)
        response.raise_for_status()
        document = response.json()
        jwks_uri = str(document.get("jwks_uri") or "").strip()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise RuntimeError(
            "OIDC discovery failed. Set MCP_AUTH_JWKS_URL explicitly or fix MCP_AUTH_ISSUER."
        ) from exc
    parsed = urlparse(jwks_uri)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("OIDC discovery returned an invalid jwks_uri")
    return jwks_uri


class OIDCTokenVerifier(TokenVerifier):
    """Validate JWT access tokens from a configured OIDC/OAuth authorization server."""

    def __init__(self) -> None:
        self.allow_local = os.environ.get("MCP_ALLOW_INSECURE_LOCAL", "").lower() in {"1", "true", "yes"}
        self.dev_token = os.environ.get("MCP_DEV_BEARER_TOKEN", "") if self.allow_local else ""
        self.dev_email = os.environ.get("MCP_DEV_USER_EMAIL", "") if self.allow_local else ""
        self.issuer = _https_url("MCP_AUTH_ISSUER", required=not self.dev_token)
        self.audience = os.environ.get("MCP_AUTH_AUDIENCE", "").strip()
        if not self.audience and not self.dev_token:
            raise RuntimeError("MCP_AUTH_AUDIENCE is required")
        self.jwks_url = _jwks_url(self.issuer)
        self.jwks = jwt.PyJWKClient(self.jwks_url) if self.jwks_url else None
        self.user_claim = os.environ.get("MCP_AUTH_USER_CLAIM", "email").strip() or "email"
        self.required_scope = os.environ.get("MCP_REQUIRED_SCOPE", "").strip()
        self.resource = os.environ.get("MCP_RESOURCE_URL", "").strip()

    async def verify_token(self, token: str) -> AccessToken | None:
        if self.dev_token and token == self.dev_token:
            if not self.dev_email:
                return None
            return AccessToken(
                token=token,
                client_id="local-dev",
                scopes=[self.required_scope] if self.required_scope else ["content-engine"],
                subject=self.dev_email.lower(),
                resource=self.resource or None,
                claims={self.user_claim: self.dev_email.lower(), "email": self.dev_email.lower()},
            )
        if not self.jwks:
            return None
        try:
            signing_key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)
            claims = await asyncio.to_thread(
                jwt.decode,
                token,
                signing_key.key,
                algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except (jwt.PyJWTError, ValueError, TypeError):
            return None
        identity = str(claims.get(self.user_claim) or claims.get("email") or "").strip().lower()
        if not identity:
            return None
        raw_scope = claims.get("scope", claims.get("scp", ""))
        if isinstance(raw_scope, str):
            scopes = raw_scope.split()
        elif isinstance(raw_scope, list):
            scopes = [str(item) for item in raw_scope]
        else:
            scopes = []
        if self.required_scope and self.required_scope not in scopes:
            return None
        raw_audience = claims.get("aud")
        audience_label = raw_audience[0] if isinstance(raw_audience, list) and raw_audience else raw_audience
        client_id = str(claims.get("azp") or claims.get("client_id") or audience_label or "chatgpt")
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(claims["exp"]),
            subject=str(claims["sub"]),
            resource=self.resource or None,
            claims={**claims, "content_engine_user": identity},
        )


def current_django_user():
    token = get_access_token()
    if token is None:
        raise OperatorError("MCP-anropet saknar autentiserad användare.")
    claims = token.claims or {}
    identity = str(
        claims.get("content_engine_user")
        or claims.get(os.environ.get("MCP_AUTH_USER_CLAIM", "email"))
        or claims.get("email")
        or ""
    ).strip().lower()
    if not identity:
        raise OperatorError("Access token saknar användaridentitet som kan mappas till Content Engine.")
    User = get_user_model()
    users = list(User.objects.filter(Q(email__iexact=identity) | Q(username__iexact=identity))[:2])
    if len(users) != 1 or not users[0].is_active:
        raise OperatorError("Den autentiserade identiteten är inte entydigt kopplad till en aktiv Content Engine-användare.")
    return users[0]
