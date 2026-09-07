import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "brightbean-studio"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
