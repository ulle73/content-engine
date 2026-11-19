"""Godkänn: send one finished file to Google Drive CONTENT/01 Publicerat (docs/designs/mallmotor.md, step 5).

The file never passes n8n. scripts/drive_upload.py asks the n8n flow "CE – Publicera till CONTENT" for a resumable
upload URL (the flow has the folder id fixed and can only create files there) and the server streams the file from
media storage straight to Google. Every approval is a Publicering row:

    <kampanj>_<stad>_<variant>_<format>_v<NN>.<ext>     e.g. golfare-i-stad_goteborg_a_4x5_v01.jpg

The version is counted under a row lock. A retry continues the same row with the same upload_url, and a row that
already has a Drive id is never uploaded again. A short card is posted in the company's Discord review channel.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from django.db import IntegrityError, transaction
from django.db.models import Max

from engine.media_storage import MediaError, open_asset

from .models import Publicering, SmsFilmOutput
from .spec import SmsFilmError

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
EXT = {"image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4"}


@lru_cache(maxsize=1)
def drive():
    spec = importlib.util.spec_from_file_location("drive_upload", ROOT / "scripts" / "drive_upload.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sakert_namn(text: str, *, falt: str, max_len: int) -> str:
    """Lowercase, å/ä→a, ö→o (and other accents dropped), spaces→hyphen, only a–z, 0–9 and hyphens."""
    s = unicodedata.normalize("NFKD", str(text or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")[:max_len].strip("-")
    if not s:
        raise SmsFilmError(f"{falt}: skriv minst en bokstav eller siffra.")
    return s


def filnamn(kampanj, stad, variant, format, version, ext) -> str:
    return f"{kampanj}_{stad}_{variant}_{format}_v{version:02d}.{ext}"


def forslag(output: SmsFilmOutput) -> dict:
    """What the approve dialog starts with: the template as campaign, the city from the values, variant a."""
    varden = output.job.varden or {}
    return {"kampanj": sakert_namn(output.job.mall_id.replace("golfkuponger-", "") or "content", falt="Kampanj", max_len=60),
            "stad": sakert_namn(varden.get("stad") or "alla", falt="Stad", max_len=60), "variant": "a"}


def godkann(output: SmsFilmOutput, user, *, kampanj, stad, variant) -> Publicering:
    """A new row with the next version. Two approvals at the same time get different numbers."""
    kampanj = sakert_namn(kampanj, falt="Kampanj", max_len=60)
    stad = sakert_namn(stad, falt="Stad", max_len=60)
    variant = sakert_namn(variant or "a", falt="Variant", max_len=30)
    asset = output.asset
    ext = EXT.get(asset.mime_type)
    if ext is None:
        raise SmsFilmError("Filen är varken JPG, PNG eller MP4 och kan inte publiceras.")
    for _ in range(5):
        try:
            with transaction.atomic():
                samma = Publicering.objects.select_for_update().filter(
                    company=output.job.company, kampanj=kampanj, stad=stad, variant=variant, format=output.format)
                version = (samma.aggregate(m=Max("version"))["m"] or 0) + 1
                return Publicering.objects.create(
                    company=output.job.company, output=output, created_by=user, kampanj=kampanj, stad=stad,
                    variant=variant, format=output.format, version=version,
                    filnamn=filnamn(kampanj, stad, variant, output.format, version, ext))
        except IntegrityError:
            continue   # someone else took the number between the lock and the insert (first row of a series)
    raise SmsFilmError("Kunde inte räkna fram ett versionsnummer. Försök igen.")


def ladda_upp(pub: Publicering) -> Publicering:
    """Upload (or continue) one approved file. Safe to call again: a finished row is left alone."""
    if pub.drive_id:
        return pub
    d = drive()
    asset = pub.output.asset
    size = asset.byte_size
    Publicering.objects.filter(pk=pub.pk).update(status="laddar", fel="")
    try:
        offset = 0
        if pub.upload_url:
            try:
                svar = d.status(pub.upload_url, size)
                if isinstance(svar, dict):
                    return _klar(pub, svar)
                offset = svar
            except d.DriveFel as exc:
                if not exc.sessionen_slut:
                    raise
                pub.upload_url = ""
        if not pub.upload_url:
            pub.upload_url = d.publicera_session(pub.filnamn, size)
            Publicering.objects.filter(pk=pub.pk).update(upload_url=pub.upload_url)
            offset = 0
        with open_asset(asset) as stream:
            meta = d.put_stream(pub.upload_url, stream, size, asset.mime_type, offset=offset)
        return _klar(pub, meta)
    except (d.DriveFel, MediaError) as exc:
        pub.status, pub.fel = "fel", str(exc)[:300]
        Publicering.objects.filter(pk=pub.pk).update(status="fel", fel=pub.fel)
        log.warning("Publicering %s misslyckades: %s", pub.pk, pub.fel)
        return pub


def _klar(pub: Publicering, meta: dict) -> Publicering:
    drive_id = str(meta.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,100}", drive_id):
        raise drive().DriveFel("Google gav inget fil-id.")
    pub.drive_id, pub.status, pub.fel = drive_id, "klar", ""
    pub.lank = f"https://drive.google.com/file/d/{drive_id}/view"
    pub.save(update_fields=["drive_id", "status", "fel", "lank", "updated_at"])
    _discord(pub)
    return pub


def _discord(pub: Publicering) -> None:
    """A short card in the review channel. Publishing never fails because Discord does."""
    if pub.discord_skickad:
        return
    from engine.review import discord, service as review_service

    company = pub.company
    payload = {"channel_id": getattr(company, "review_channel_id", ""), "attachment": None,
               "message": {"content": f"📁 Ny fil i CONTENT/01 Publicerat: **{pub.filnamn}**\n{pub.lank}"}}
    try:
        discord.post(payload, company)
    except review_service.ReviewError as exc:
        log.info("Publicering %s: Discord-kortet skickades inte (%s)", pub.pk, exc)
        return
    pub.discord_skickad = True
    pub.save(update_fields=["discord_skickad", "updated_at"])


def serialize(pub: Publicering) -> dict:
    return {"id": str(pub.pk), "status": pub.status, "status_label": pub.get_status_display(), "filnamn": pub.filnamn,
            "lank": pub.lank, "fel": pub.fel, "version": pub.version}
