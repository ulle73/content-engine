"""Settings used only by the public Content Engine MCP/OAuth service."""

import os

from .settings import *  # noqa: F403

# Django ASGI must not retain per-thread persistent connections. Neon provides
# the pool; each request releases its connection back to that pool.
DATABASES["default"]["CONN_MAX_AGE"] = 0
if not LOCAL_HTTP and os.environ.get("MCP_ALLOW_INSECURE_LOCAL", "").lower() in {"1", "true", "yes"}:
    raise ImproperlyConfigured("Local MCP authentication must not be enabled in production.")

ROOT_URLCONF = "engine.mcp_auth_urls"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"

MCP_PUBLIC_URL = APP_URL.rstrip("/")  # noqa: F405
MCP_RESOURCE_URL = os.environ.get("MCP_RESOURCE_URL", f"{MCP_PUBLIC_URL}/mcp").rstrip("/")
MCP_REQUIRED_SCOPE = os.environ.get("MCP_REQUIRED_SCOPE", "content-engine.operate").strip() or "content-engine.operate"
MCP_OAUTH_ALLOWED_CLIENT_HOSTS = [
    item.strip().lower()
    for item in os.environ.get(
        "MCP_OAUTH_ALLOWED_CLIENT_HOSTS",
        "chatgpt.com,openai.com,connectors.api.openai.org",
    ).split(",")
    if item.strip()
]

# Content Engine is its own OAuth authorization server for the MCP service.
# The same Django users/passwords and same database are used; no external IdP is required.
OAUTH2_PROVIDER = {
    "OIDC_ISS_ENDPOINT": MCP_PUBLIC_URL,
    "SCOPES": {
        MCP_REQUIRED_SCOPE: "Operate the authenticated user's Content Engine companies",
        "offline_access": "Keep the ChatGPT connection active with refresh tokens",
    },
    "DEFAULT_SCOPES": [MCP_REQUIRED_SCOPE],
    "ACCESS_TOKEN_EXPIRE_SECONDS": 3600,
    "REFRESH_TOKEN_EXPIRE_SECONDS": 90 * 24 * 60 * 60,
    "ROTATE_REFRESH_TOKEN": True,
    "REFRESH_TOKEN_REUSE_PROTECTION": True,
    "REFRESH_TOKEN_GRACE_PERIOD_SECONDS": 0,
    "PKCE_REQUIRED": True,
    "ALLOW_URI_WILDCARDS": False,
    "ALLOW_LOCALHOST_LOOPBACK": LOCAL_HTTP,  # noqa: F405
    "ALLOWED_REDIRECT_URI_SCHEMES": ["http", "https"] if LOCAL_HTTP else ["https"],  # noqa: F405
    "DCR_ENABLED": True,
    "DCR_REGISTRATION_PERMISSION_CLASSES": ("engine.mcp_oauth.ChatGPTDCRPermission",),
    "DCR_REGISTRATION_TOKEN_EXPIRE_SECONDS": 3600,
    "DCR_ROTATE_REGISTRATION_TOKEN_ON_UPDATE": True,
    # Prefer ChatGPT's stable CIMD identity. django-oauth-toolkit 3.4.1 only
    # wires public clients into CIMD, while ChatGPT's transition document lists
    # both "none" and "private_key_jwt". The custom fetcher selects the mutually
    # supported public PKCE method without weakening the host allowlist.
    "CIMD_ENABLED": True,
    "CIMD_METADATA_FETCHER": "engine.mcp_oauth.ChatGPTCIMDMetadataFetcher",
    "CIMD_REGISTRATION_PERMISSION_CLASSES": ("oauth2_provider.cimd.HostAllowlistCIMDPermission",),
    "CIMD_ALLOWED_HOSTS": MCP_OAUTH_ALLOWED_CLIENT_HOSTS,
    "OAUTH2_RESPONSE_TYPES_SUPPORTED": ["code"],
    "OAUTH2_GRANT_TYPES_SUPPORTED": ["authorization_code", "refresh_token"],
    "OAUTH2_TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED": ["none", "client_secret_basic", "client_secret_post"],
    "OAUTH2_PROTECTED_RESOURCE_IDENTIFIER": MCP_RESOURCE_URL,
    "OAUTH2_PROTECTED_RESOURCE_AUTHORIZATION_SERVERS": [MCP_PUBLIC_URL],
    # Adopt OAuth 2.0 Security BCP / OAuth 2.1 posture now instead of relying on future defaults.
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,
    "COMPLIANT_BCP_RFC9700_ACCESS_TOKEN_TRANSPORT": True,
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,
    "COMPLIANT_BCP_RFC9700_REFRESH_TOKEN": True,
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_SCHEME": not LOCAL_HTTP,  # noqa: F405
    "COMPLIANT_BCP_RFC9700_REDIRECT_URI_MATCHING": True,
    "COMPLIANT_BCP_RFC9700_PKCE_REQUIRED": True,
}
