"""Brightbean configuration. Same application locally and on the production host."""

import os
from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured

ENGINE_ROOT = Path(__file__).resolve().parent.parent
environ.Env.read_env(ENGINE_ROOT / ".env", overwrite=False)
if os.environ.get('RENDER_EXTERNAL_URL'):
    os.environ.setdefault('APP_URL', os.environ['RENDER_EXTERNAL_URL'])
    os.environ.setdefault('ALLOWED_HOSTS', urlparse(os.environ['RENDER_EXTERNAL_URL']).hostname)
from config.settings.base import *  # noqa: E402,F403

DEBUG = False
INSTALLED_APPS = [*INSTALLED_APPS, "engine"]  # noqa: F405
ROOT_URLCONF = "engine.urls"
WSGI_APPLICATION = "engine.wsgi.application"
LANGUAGE_CODE = "sv"
TIME_ZONE = "Europe/Stockholm"
STATIC_ROOT = ENGINE_ROOT / "staticfiles"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(ENGINE_ROOT / "data" / "media"))
TEMPLATES[0]["DIRS"].insert(0, ENGINE_ROOT / "templates")  # noqa: F405
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
ACCOUNT_ADAPTER = "engine.accounts.AccountAdapter"
ACCOUNT_ALLOW_REGISTRATION = False
MIDDLEWARE = [item for item in MIDDLEWARE if item != "apps.accounts.middleware.TosAcceptanceMiddleware"]  # noqa: F405

# TLS is terminated by the deployment's reverse proxy. Plain HTTP is local only.
app_host = urlparse(APP_URL).hostname  # noqa: F405
LOCAL_HTTP = app_host in {"127.0.0.1", "localhost"} and APP_URL.startswith("http://")  # noqa: F405
if not LOCAL_HTTP:
    if not APP_URL.startswith("https://"):  # noqa: F405
        raise ImproperlyConfigured("APP_URL must use HTTPS outside localhost.")
    if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":  # noqa: F405
        raise ImproperlyConfigured("Set DATABASE_URL to PostgreSQL for production.")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = [APP_URL.rstrip("/")]  # noqa: F405
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
    DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
    if DATABASES["default"]["ENGINE"].endswith("sqlite3"):  # noqa: F405
        DATABASES["default"]["OPTIONS"]["timeout"] = 30  # noqa: F405
