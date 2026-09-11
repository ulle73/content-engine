"""Serialize production migrations when web and MCP Render services deploy concurrently."""

import os

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
