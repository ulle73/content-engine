from config.urls import urlpatterns as brightbean_urls
from django.urls import include, path

from . import views

engine_urls = [
    path("", views.home, name="home"),
    path("ideas/", views.ideas, name="ideas"),
    path("connect/", views.connect, name="connect"),
    path("runs/<uuid:run_id>/", views.review, name="review"),
    path("runs/<uuid:run_id>/draft/<int:idea_index>/", views.draft, name="draft"),
]
urlpatterns = [
    path("source/", views.source_code, name="source_code"),
    path("", views.index, name="dashboard"),
    path("workspace/<uuid:workspace_id>/content/", include((engine_urls, "engine"))),
    *(route for route in brightbean_urls if str(route.pattern) != ""),
]
