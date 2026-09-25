"""Small policy hooks for the self-hosted MCP OAuth authorization server."""

import json
import os
from urllib.parse import urlparse

from oauth2_provider.cimd import SafeMetadataFetcher


def allowed_chatgpt_hosts() -> set[str]:
    raw = os.environ.get(
        "MCP_OAUTH_ALLOWED_CLIENT_HOSTS",
        "chatgpt.com,openai.com,connectors.api.openai.org",
    )
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


class ChatGPTCIMDMetadataFetcher(SafeMetadataFetcher):
    """Adapt ChatGPT's transition CIMD metadata to this server's public PKCE support.

    ChatGPT's stable CIMD document currently keeps private_key_jwt in the legacy
    singular field as a preference while also advertising an unordered supported
    methods list containing "none". django-oauth-toolkit 3.4.1 only wires public
    clients into CIMD, so select "none" when ChatGPT explicitly advertises it.
    The normal CIMD host allowlist and PKCE requirements remain in force.
    """

    def fetch(self, client_id):
        metadata, max_age = super().fetch(client_id)
        host = urlparse(client_id).hostname
        supported_methods = metadata.get("token_endpoint_auth_methods_supported")
        if (
            host
            and host.lower() in allowed_chatgpt_hosts()
            and isinstance(supported_methods, list)
            and "none" in supported_methods
            and metadata.get("token_endpoint_auth_method") != "none"
        ):
            metadata = dict(metadata)
            metadata["token_endpoint_auth_method"] = "none"
        return metadata, max_age


class ChatGPTDCRPermission:
    """Allow anonymous DCR only for HTTPS callbacks on explicitly trusted OpenAI hosts.

    Dynamic registration has to be reachable before the user can authenticate, but it must
    not become a general-purpose public OAuth-client registry. Content access still requires
    the user's normal Content Engine login and consent after registration.
    """

    def has_permission(self, request) -> bool:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, AttributeError):
            return False
        if not isinstance(payload, dict):
            return False
        redirect_uris = payload.get("redirect_uris")
        if not isinstance(redirect_uris, list) or not redirect_uris:
            return False
        allowed_hosts = allowed_chatgpt_hosts()
        for value in redirect_uris:
            if not isinstance(value, str):
                return False
            try:
                parsed = urlparse(value)
                if parsed.port not in (None, 443):
                    return False
            except ValueError:
                return False
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.hostname.lower() not in allowed_hosts
                or parsed.username
                or parsed.password
                or parsed.fragment
            ):
                return False
        grant_types = payload.get("grant_types") or ["authorization_code"]
        if not isinstance(grant_types, list) or not all(isinstance(grant, str) for grant in grant_types) or not set(grant_types).issubset({"authorization_code", "refresh_token"}):
            return False
        auth_method = payload.get("token_endpoint_auth_method", "client_secret_basic")
        if auth_method not in {"none", "client_secret_basic", "client_secret_post"}:
            return False
        return True
