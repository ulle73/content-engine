#!/usr/bin/env bash
set -euo pipefail
git submodule update --init --recursive
pip install -r requirements.txt
npm --prefix vendor/brightbean-studio/theme/static_src ci
npm --prefix vendor/brightbean-studio/theme/static_src run build
python manage.py collectstatic --noinput
python scripts/source_archive.py
