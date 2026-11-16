"""Pack Apple's private iMessage files from the local cache and store them privately for the SMS film renderer.

The repo is public, so fonts, emoji, iOS sounds and the phone frame never go into git or the Actions cache.
Run locally with the production R2 settings in the environment:

    python manage.py sms_film_apple_pack            # reads $IMESSAGE_CACHE or ~/.cache/imessage-mall
    python manage.py sms_film_apple_pack --dry-run  # lists what would be packed
"""

import io
import os
import tarfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from engine import media_storage
from engine.smsfilm.service import APPLE_PACK_KEY

FILES = [
    "fonts/SF-Pro-Text-Regular.otf", "fonts/SF-Pro-Text-Medium.otf", "fonts/SF-Pro-Text-Semibold.otf",
    "fonts/SF-Pro-Display-Regular.otf", "fonts/SF-Pro-Display-Semibold.otf",
    "AppleColorEmoji-Linux.ttf", "iphone-17.png",
    *(f"ljud/{n}.wav" for n in ("SentMessage", "ReceivedMessage", "key_press_click", "key_press_delete",
                                "key_press_modifier", "Tritone", "Rebound")),
]


def build_pack(cache: Path) -> bytes:
    missing = [f for f in FILES if not (cache / f).is_file()]
    if missing:
        raise CommandError(f"Saknas i {cache}: {', '.join(missing)}. Kör först: node library/templates/imessage-samtal/apple-resurser.mjs")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in FILES:
            info = tar.gettarinfo(str(cache / name), arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o644
            with (cache / name).open("rb") as f:
                tar.addfile(info, f)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Packar Apples typsnitt, emoji, iOS-ljud och telefonram och sparar dem privat för SMS-filmen."

    def add_arguments(self, parser):
        parser.add_argument("--cache", default=os.environ.get("IMESSAGE_CACHE") or str(Path.home() / ".cache" / "imessage-mall"))
        parser.add_argument("--backend", choices=["local", "r2"], default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, cache, backend, dry_run, **options):
        data = build_pack(Path(cache))
        if dry_run:
            self.stdout.write(f"{len(FILES)} filer, {len(data) / 1e6:.1f} MB – inget sparat.")
            return
        try:
            used = media_storage.put(APPLE_PACK_KEY, data, "application/gzip", backend=backend)
        except media_storage.MediaError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Apple-paketet sparat ({used}, {len(data) / 1e6:.1f} MB)."))
