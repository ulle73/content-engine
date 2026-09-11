#!/usr/bin/env bash
set -euo pipefail
export DJANGO_SETTINGS_MODULE=engine.mcp_settings
python scripts/migrate_locked.py
exec uvicorn engine.mcp_app:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
