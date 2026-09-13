"""Serialize production migrations when web and MCP Render services deploy concurrently."""

import os
import sys
from pathlib import Path

# When Render executes this file directly, Python puts scripts/ (not the repo
# root) on sys.path. Add the project root so the engine package is importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")

import django

django.setup()

from django.core.management import call_command
from django.db import connection

LOCK_ID = 730092


def main():
    if connection.vendor != "postgresql":
        call_command("migrate", interactive=False)
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [LOCK_ID])
    try:
        call_command("migrate", interactive=False)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])


if __name__ == "__main__":
    main()
