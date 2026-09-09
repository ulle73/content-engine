from django.contrib.auth.views import LogoutView
from django.http import JsonResponse
from django.urls import include, path

from . import ads_views, intelligence_views, media_views, views
from .onboarding import SignInView, setup
from .company_settings import company_settings
from .performance_views import performance

engine_urls = [
    path("intelligence/own/",performance,name="own_performance"),
    path("intelligence/ads/accounts/<int:account_id>/", ads_views.account_action, name="ad_account_action"),
    path("intelligence/ads/analyze/<int:ad_id>/", ads_views.analyze, name="ad_analyze"),
    path("runs/<uuid:run_id>/outcome/", ads_views.outcome, name="outcome"),
    path("settings/", company_settings, name="settings"),
    path("media/<uuid:asset_id>/file/", media_views.asset_file, name="asset_file"),
    path("runs/<uuid:run_id>/media/", media_views.picker, name="media"),
    path("runs/<uuid:run_id>/media/upload/", media_views.upload, name="media_upload"),
    path("runs/<uuid:run_id>/media/generate/", media_views.generate_media, name="media_generate"),
    path("runs/<uuid:run_id>/media/jobs/<uuid:job_id>/", media_views.job_page, name="media_job"),
    path("runs/<uuid:run_id>/media/jobs/<uuid:job_id>/status/", media_views.job_status, name="media_job_status"),
    path("runs/<uuid:run_id>/media/jobs/<uuid:job_id>/reset/", media_views.reset_job, name="media_job_reset"),
    path("runs/<uuid:run_id>/media/<uuid:asset_id>/use/", media_views.use_asset, name="media_use"),
    path("runs/<uuid:run_id>/media/<uuid:asset_id>/delete/", media_views.delete_asset, name="media_delete"),
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
