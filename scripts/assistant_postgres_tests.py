"""Run assistant approval/concurrency checks against the isolated local PG fixture.

Never loads .env. Only 127.0.0.1:55439 and the named disposable test DB are used.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "engine.test_settings"
import engine.test_settings as config

config.DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "postgres", "USER": "postgres",
                                "HOST": "127.0.0.1", "PORT": "55439", "TEST": {"NAME": "content_engine_assistant_test"}}}
import django

django.setup()
from django.conf import settings
from django.test.utils import get_runner

failures = get_runner(settings)(verbosity=1, interactive=False).run_tests(["engine.test_assistant", "engine.test_media_concurrency"])
raise SystemExit(bool(failures))
