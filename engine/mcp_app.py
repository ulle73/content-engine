"""Combined ASGI app: protected MCP first, Content Engine OAuth/login as fallback."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.mcp_settings")

base_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/") or "http://127.0.0.1:8766"
os.environ.setdefault("MCP_AUTH_ISSUER", base_url)
os.environ.setdefault("MCP_RESOURCE_URL", base_url + "/mcp")

from django.core.asgi import get_asgi_application
from starlette.routing import Mount

from . import mcp_server
from .media_recovery import install_recovery


app = mcp_server.build_app()
install_recovery(app)
# MCP and its RFC 9728 metadata stay first. Browser-based OAuth/login is served by
# Django for every remaining route on the same origin, keeping deployment to one service.
app.routes.append(Mount("/", app=get_asgi_application()))
