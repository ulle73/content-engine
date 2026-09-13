"""Explicit isolated PostgreSQL tests, never the configured production URL."""
import os

from .test_settings import *

test_url = os.environ.get("TEST_DATABASE_URL", "")
if not test_url:
    raise ImproperlyConfigured("TEST_DATABASE_URL is required for PostgreSQL tests")
DATABASES = {"default": env.db_url_config(test_url)}
