"""Company-scoped storage measurements; never expose keys or account-wide usage."""

import hashlib
import os
import shutil
import time
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Sum
from django.template.defaultfilters import filesizeformat
from django.utils import timezone

from .media_storage import MediaError, local_path, r2


def registered_usage(company):
    totals = company.media_assets.aggregate(files=Count("pk"), bytes=Sum("byte_size"))
    cloud = settings.MEDIA_STORAGE == "r2" or company.media_assets.filter(storage_backend="r2").exists()
    return {
        "registered_files": totals["files"],
        "registered_bytes": totals["bytes"] or 0,
        "used_label": filesizeformat(totals["bytes"] or 0),
        "used_caption": "Mediafiler i databasen",
        "capacity_label": "Ingen fast diskstorlek" if cloud else "Hämtar…",
        "free_label": "Skalar vid behov" if cloud else "Hämtar…",
        "backend_label": "Cloudflare R2" if cloud else "Lokal disk",
        "detail": "Hämtar faktisk användning, inklusive original och interna kopior…",
        "updated_label": "",
        "measured": False,
        "cloud": cloud,
    }


def _local_usage(company):
    root = Path(settings.MEDIA_ROOT).resolve()
    # A missing media folder does not mean the volume is unavailable.
    volume_path = root
    while not volume_path.exists() and volume_path != volume_path.parent:
        volume_path = volume_path.parent
    volume = shutil.disk_usage(volume_path)
    if (root / str(company.pk)).is_symlink():
        raise MediaError("Lagringsmappen kunde inte verifieras.")
    folder = local_path(str(company.pk))
    files = []
    if folder.is_dir():
        for path in folder.rglob("*"):
            # Do not follow links into another company's files or another volume.
            if path.is_symlink() or not path.resolve().is_relative_to(folder):
                continue
            if path.is_file():
                files.append(path.stat().st_size)
    return sum(files), len(files), volume


def _r2_usage(company):
    client = r2(metrics=True)
    prefix = str(company.pk) + "/"
    total = count = 0
    token = None
    started = time.monotonic()
    # Bound work even for a very large company; partial totals are explicitly labelled.
    for _ in range(10):
        params = {"Bucket": os.environ["R2_BUCKET_NAME"], "Prefix": prefix, "MaxKeys": 1000}
        if token:
            params["ContinuationToken"] = token
        page = client.list_objects_v2(**params)
        for item in page.get("Contents", []):
            if not item["Key"].startswith(prefix) or int(item["Size"]) < 0:
                raise MediaError("Lagringssvaret kunde inte verifieras.")
            total += int(item["Size"])
            count += 1
        if not page.get("IsTruncated"):
            return total, count, True
        next_token = page.get("NextContinuationToken")
        if not next_token or next_token == token:
            raise MediaError("Lagringssvaret kunde inte verifieras.")
        token = next_token
        if time.monotonic() - started >= 15:
            break
    return total, count, False


def storage_usage(company, *, refresh=False):
    result = registered_usage(company)
    # Storage backend/configuration changes must not reuse an old measurement.
    config = "|".join(str(value) for value in (settings.MEDIA_ROOT, settings.MEDIA_STORAGE,
                      os.environ.get("R2_BUCKET_NAME", ""), os.environ.get("R2_ACCOUNT_ID", ""), os.environ.get("R2_ENDPOINT_URL", "")))
    key = f"media-usage:{company.pk}:{hashlib.sha256(config.encode()).hexdigest()[:20]}"
    snapshot = None if refresh else cache.get(key)
    if snapshot:
        return {**result, **snapshot}
    try:
        cloud = result["cloud"]
        total = count = 0
        complete = True
        if cloud:
            total, count, complete = _r2_usage(company)
        volume = None
        if not cloud or company.media_assets.filter(storage_backend="local").exists():
            local_bytes, local_files, volume = _local_usage(company)
            total += local_bytes
            count += local_files
        detail = f"{count} lagrade filer, inklusive original, förhandsvisningar och interna kopior."
        if cloud:
            detail += " R2 har ingen fast diskstorlek; lagringskostnaden baseras på användning."
        else:
            detail += " Totalstorlek och ledigt utrymme gäller hela disken, som kan innehålla annat än media."
        if not complete:
            detail = "Minst " + detail + " Mätningen nådde sin tids- eller filgräns; totalsumman är inte fullständig."
        snapshot = {
            "used_bytes": total, "stored_files": count,
            "used_caption": "Använt lagringsutrymme",
            "used_label": ("Minst " if not complete else "") + str(filesizeformat(total)),
            "capacity_bytes": volume.total if not cloud else None,
            "free_bytes": volume.free if not cloud else None,
            "capacity_label": filesizeformat(volume.total) if not cloud else "Ingen fast diskstorlek",
            "free_label": filesizeformat(volume.free) if not cloud else "Skalar vid behov",
            "detail": detail, "measured": True, "complete": complete,
            "updated_label": "Uppdaterat " + timezone.localtime().strftime("%H:%M:%S"),
        }
        cache.set(key, snapshot, timeout=60)
        return {**result, **snapshot}
    except (MediaError, OSError, BotoCoreError, ClientError, KeyError, ValueError, TypeError):
        return {**result, "detail": "Faktisk lagring kunde inte mätas. Visar registrerade mediafilers storlek från databasen; extra original och interna kopior ingår inte.",
                "capacity_label": result["capacity_label"] if result["cloud"] else "Kan inte mätas",
                "free_label": result["free_label"] if result["cloud"] else "Kan inte mätas",
                "updated_label": "Försök uppdatera igen."}
