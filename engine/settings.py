"""Small standalone Django application; publishing belongs to hosted Postiz."""

import os
from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured

ENGINE_ROOT = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(ENGINE_ROOT / ".env", overwrite=False)
SECRET_KEY = env("SECRET_KEY")
APP_URL = os.environ.get("RENDER_EXTERNAL_URL") or env("APP_URL", default="http://127.0.0.1:8765")
LOCAL_HTTP = urlparse(APP_URL).hostname in {"127.0.0.1", "localhost"} and APP_URL.startswith("http://")
DEBUG = False
ALLOWED_HOSTS = [urlparse(APP_URL).hostname]
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{ENGINE_ROOT / 'data' / 'app.sqlite3'}")}
if DATABASES["default"]["ENGINE"].endswith("postgresql"):
    DATABASES["default"]["CONN_MAX_AGE"] = 60
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "engine",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "engine.urls"
WSGI_APPLICATION = "engine.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [ENGINE_ROOT / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
]
LANGUAGE_CODE = "sv"
TIME_ZONE = "Europe/Stockholm"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = ENGINE_ROOT / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if LOCAL_HTTP
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
# Local development uses Waitress with DEBUG off, so WhiteNoise must read app static files directly.
WHITENOISE_USE_FINDERS = LOCAL_HTTP
WHITENOISE_AUTOREFRESH = LOCAL_HTTP
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-5.6-luna")
SETUP_TOKEN = env("SETUP_TOKEN", default="")
# Dedicated encryption secret, stable across deployments. No upstream field implementation.
POSTIZ_ENCRYPTION_SECRET = env("POSTIZ_ENCRYPTION_SECRET", default=SECRET_KEY)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
MEDIA_STORAGE = env("MEDIA_STORAGE", default="r2" if env("R2_ENDPOINT_URL", default="") or env("R2_ACCOUNT_ID", default="") or not LOCAL_HTTP else "local")
MEDIA_ROOT = ENGINE_ROOT / "media"
OPENAI_IMAGE_MODEL = env("OPENAI_IMAGE_MODEL", default="gpt-image-2")
# Official Higgsfield OpenAPI, checked 2026-09-08. Model names stay out of the editor UI.
HIGGSFIELD_VIDEO_MODEL = "kling-video/v2.5-turbo/pro"
if LOCAL_HTTP:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "testserver"]
else:
    if not APP_URL.startswith("https://"):
        raise ImproperlyConfigured("APP_URL must use HTTPS outside localhost.")
    if not DATABASES["default"]["ENGINE"].endswith("postgresql"):
        raise ImproperlyConfigured("Production requires PostgreSQL.")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = [APP_URL.rstrip("/")]
