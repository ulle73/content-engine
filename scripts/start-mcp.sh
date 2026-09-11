#!/usr/bin/env bash
set -euo pipefail
python scripts/migrate_locked.py
exec uvicorn engine.mcp_server:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
