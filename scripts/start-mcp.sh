#!/usr/bin/env bash
set -euo pipefail
export DJANGO_SETTINGS_MODULE=engine.mcp_settings
python scripts/migrate_locked.py
if [[ -n "${D2_HIGGSFIELD_PREFLIGHT_TOKEN:-}" && "${D2_HIGGSFIELD_PREFLIGHT_TOKEN}" != "0" ]]; then
  python manage.py d2_higgsfield_preflight --token "${D2_HIGGSFIELD_PREFLIGHT_TOKEN}"
fi
exec uvicorn engine.mcp_app:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
