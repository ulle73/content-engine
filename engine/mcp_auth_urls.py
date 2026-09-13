"""Browser-facing login/consent and OAuth endpoints for the MCP service."""

from django.contrib.auth.views import LogoutView
from django.http import JsonResponse
from django.urls import include, path
from oauth2_provider.urls import metadata_urlpatterns

from .onboarding import SignInView, setup


def auth_home(request):
    return JsonResponse(
        {
            "service": "Content Engine MCP OAuth",
            "authenticated": bool(request.user.is_authenticated),
        }
    )


urlpatterns = [
    # RFC 8414/RFC 9728 well-known discovery at the domain root.
    path(
        "",
        include((metadata_urlpatterns, "oauth2_provider"), namespace="oauth2_metadata"),
    ),
    path("oauth/", include("oauth2_provider.urls")),
    path("accounts/login/", SignInView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("setup/", setup, name="setup"),
    path("oauth/status/", auth_home, name="oauth_home"),
    # Serve the existing editor on this same deployment. Its named dashboard
    # route is also required by login/setup templates and OAuth return flows.
    path("", include("engine.urls")),
]
