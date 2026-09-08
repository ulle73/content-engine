from django.contrib.auth.views import LogoutView
from django.http import JsonResponse
from django.urls import include, path

from . import intelligence_views, views
from .onboarding import SignInView, setup

engine_urls = [
    path("intelligence/", intelligence_views.intelligence, name="intelligence"),
    path("intelligence/refresh/", intelligence_views.refresh_imports, name="refresh_imports"),
    path("intelligence/accounts/<int:competitor_id>/", intelligence_views.competitor_action, name="competitor_action"),
    path("intelligence/analyze/<int:post_id>/", intelligence_views.analyze_signal, name="analyze_signal"),
    path("runs/<uuid:run_id>/reject/<int:idea_index>/", intelligence_views.reject_idea, name="reject_idea"),
    path("", views.home, name="home"),
    path("ideas/", views.ideas, name="ideas"),
    path("connect/", views.connect, name="connect"),
    path("runs/<uuid:run_id>/", views.review, name="review"),
    path("runs/<uuid:run_id>/draft/<int:idea_index>/", views.draft, name="draft"),
]
urlpatterns = [
    path("", views.index, name="dashboard"),
    path("setup/", setup, name="setup"),
    path("accounts/login/", SignInView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("company/<uuid:workspace_id>/", include((engine_urls, "engine"))),
]
