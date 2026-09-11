#!/usr/bin/env bash
set -euo pipefail
python scripts/migrate_locked.py
exec gunicorn engine.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 4 --timeout 360 --access-logfile -
