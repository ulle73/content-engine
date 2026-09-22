"""Lossless, fail-closed handoff between compatible Content Engine databases.

Run snapshot against the old URL, then restore/verify against the new URL.
URLs come only from the environment. Backups contain private data: keep them
outside Git in an access-controlled directory. Stop all writers before snapshot.
The destination must be migrated and contain no application/user data.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, time
from itertools import chain
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")

import django

django.setup()

from django.core.management import call_command
from django.apps import apps as registry
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction

METADATA = {"auth_permission", "django_content_type", "django_migrations"}


class ExactJSONEncoder(DjangoJSONEncoder):
    def default(self, value):
        # Django's standard JSON encoder truncates microseconds to milliseconds.
        # Predictions, outcomes, observations and leases must retain exact times.
        if isinstance(value, (datetime, time)):
            return value.isoformat()
        return super().default(value)


def inventory():
    """Hash canonical PostgreSQL rows, including primary keys and ciphertext."""
    result = {}
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL TIME ZONE 'UTC'")
        for table in sorted(connection.introspection.table_names(cursor)):
            quoted = connection.ops.quote_name(table)
            cursor.execute(f"SELECT row_to_json(t)::jsonb::text FROM {quoted} t ORDER BY row_to_json(t)::jsonb::text COLLATE \"C\"")
            digest = hashlib.sha256()
            count = 0
            for (row,) in cursor:
                digest.update(row.encode() + b"\n")
                count += 1
            result[table] = {"rows": count, "sha256": digest.hexdigest()}
    return result


def compare(expected, actual):
    mismatches = [table for table, value in expected.items()
                  if table not in METADATA and actual.get(table) != value]
    if mismatches:
        raise RuntimeError("Content mismatch in: " + ", ".join(mismatches))


def snapshot(directory):
    directory.mkdir(parents=True, exist_ok=False)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        before = inventory()
        known = METADATA | {"django_session"}
        unknown = [t for t, v in before.items() if t not in known
                   and not t.startswith(("engine_", "auth_", "operator_bridge_", "oauth2_provider_")) and v["rows"]]
        if unknown:
            raise RuntimeError("Unmapped source tables: " + ", ".join(unknown))
        apps = ["engine", "auth", "sessions"]
        if any(t.startswith("operator_bridge_") for t in before):
            apps.append("operator_bridge")
        if any(t.startswith("oauth2_provider_") for t in before):
            apps.append("oauth2_provider")
        fixture = directory / "data.json"
        models = [model for app in apps for model in registry.get_app_config(app).get_models()
                  if model._meta.db_table != "auth_permission"]
        models = serializers.sort_dependencies([(registry.get_app_config(app),
                  [m for m in models if m._meta.app_label == app]) for app in apps])
        objects = chain.from_iterable(model._default_manager.order_by(model._meta.pk.name).iterator() for model in models)
        with fixture.open("w", encoding="utf-8") as stream:
            serializers.serialize("json", objects, stream=stream,
                                  use_natural_foreign_keys=True, cls=ExactJSONEncoder)
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
            migrations = cursor.fetchall()
        manifest = {"format": 1, "tables": before, "migrations": migrations,
                    "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest()}
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Snapshot: {len(before)} tables; {sum(v['rows'] for v in before.values())} rows")


def restore(directory, *, verify_only=False):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    fixture = directory / "data.json"
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != manifest["fixture_sha256"]:
        raise RuntimeError("Backup checksum mismatch")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '15s'")
            # Block a concurrent setup/login/content write for the whole import.
            if not verify_only:
                tables = connection.introspection.table_names(cursor)
                quoted = ", ".join(connection.ops.quote_name(t) for t in tables)
                cursor.execute(f"LOCK TABLE {quoted} IN EXCLUSIVE MODE")
            cursor.execute("SELECT app, name FROM django_migrations")
            applied = set(cursor.fetchall())
        if not set(map(tuple, manifest["migrations"])).issubset(applied):
            raise RuntimeError("Target is missing source schema migrations")
        if not verify_only:
            existing = inventory()
            managed = {model._meta.db_table for model in registry.get_models(include_auto_created=True)}
            occupied = [t for t, v in existing.items() if v["rows"] and t in managed
                        and t not in METADATA | {"engine_setupstate"}]
            if occupied:
                raise RuntimeError("Target is not empty; refusing overwrite: " + ", ".join(occupied))
            call_command("loaddata", str(fixture), verbosity=0)
        current = inventory()
        compare(manifest["tables"], current)
        if not verify_only:
            # Unrelated target tables are retained verbatim, never cleared for import.
            compare({t: v for t, v in existing.items() if t not in managed}, current)
        # Exiting atomic validates deferred foreign keys before claiming success.
    print("Verified all source application/auth/session table counts and SHA-256 row digests")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["snapshot", "restore", "verify"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if connection.vendor != "postgresql":
        raise RuntimeError("This handoff requires PostgreSQL at both ends")
    if "-pooler." in connection.settings_dict.get("HOST", ""):
        raise RuntimeError("Use a direct PostgreSQL URL for migration/verification")
    if args.operation == "snapshot":
        snapshot(args.directory)
    else:
        restore(args.directory, verify_only=args.operation == "verify")


if __name__ == "__main__":
    main()
