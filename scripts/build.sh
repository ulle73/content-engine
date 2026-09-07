#!/usr/bin/env bash
set -euo pipefail
git submodule update --init vendor/social-media-skills
pip install -r requirements.txt
python manage.py collectstatic --noinput
