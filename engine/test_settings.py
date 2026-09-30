import os

# Tests must not load provider credentials or production configuration from .env.
os.environ.setdefault("SECRET_KEY", "isolated-test-secret-only")
os.environ.setdefault("APP_URL", "http://127.0.0.1:8765")
os.environ.setdefault("MCP_AUTH_ISSUER", "http://127.0.0.1:8765")
os.environ.setdefault("MCP_RESOURCE_URL", "http://127.0.0.1:8765/mcp")

from .settings import *

# Unit/integration checks must never create data in the production database.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
