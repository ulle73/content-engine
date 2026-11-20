"""Radera i Dina filer: choose where one job is removed from.

- lista: leave it out of Dina filer. The job and its files stay in Content Engine (SmsFilmJob.dold_at).
- content_engine: delete the job, its output rows and the rendered files (database and media storage). Cannot be
  undone. Publicering rows stay (output becomes NULL), so Drive version numbers are never reused.
- drive: put every file published from this job in Drive's trash through the n8n flow "CE – Papperskorg i CONTENT".
  The flow only touches files in CONTENT/01 Publicerat, and Drive keeps trashed files for 30 days.

Drive goes first: if Google cannot be reached nothing is deleted in Content Engine, so the user can try again.
The photos a user uploaded for the job are not touched; they belong to the media library.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from engine.media import asset_removal_blocker
from engine.media_storage import MediaError, delete_file
from engine.models import MediaAsset

from .models import Publicering, SmsFilmJob
from .publicera import drive
from .spec import SmsFilmError

log = logging.getLogger(__name__)
ACTIVE = ("queued", "claimed", "rendering")


def i_drive(job: SmsFilmJob) -> list[Publicering]:
    """Files from this job that are in Drive right now."""
    return list(Publicering.objects.filter(output__job=job, status="klar").exclude(drive_id="").order_by("created_at"))


def radera(job: SmsFilmJob, *, lista: bool = True, content_engine: bool = False, i_drive_ocksa: bool = False) -> dict:
    if not (lista or content_engine or i_drive_ocksa):
        raise SmsFilmError("Välj minst ett ställe att radera från.")
    if content_engine and job.status in ACTIVE:
        raise SmsFilmError("Filen skapas just nu. Vänta tills den är klar och försök igen.")
    resultat = {"drive": [], "content_engine": False, "dold": False}
    if i_drive_ocksa:
        d = drive()
        for pub in i_drive(job):
            try:
                d.papperskorg(pub.drive_id)
            except d.DriveFel as exc:
                raise SmsFilmError(f"{pub.filnamn}: {exc}") from None
            Publicering.objects.filter(pk=pub.pk).update(status="raderad", updated_at=timezone.now())
            resultat["drive"].append(pub.filnamn)
    if content_engine:
        _radera_i_content_engine(job)
        resultat["content_engine"] = True
    elif lista:
        SmsFilmJob.objects.filter(pk=job.pk).update(dold_at=timezone.now())
        resultat["dold"] = True
    return resultat


def _radera_i_content_engine(job: SmsFilmJob) -> None:
    if job.kind == "slutmall" and job.output_asset_id and SmsFilmJob.objects.filter(
            company=job.company, status__in=ACTIVE, conversation__outro__asset=str(job.output_asset_id)).exists():
        raise SmsFilmError("En SMS-film som skapas just nu slutar med den här slutmallen. Vänta tills den är klar.")
    asset_ids = {o.asset_id for o in job.outputs.all()}
    if job.output_asset_id:
        asset_ids.add(job.output_asset_id)
    with transaction.atomic():
        locked = SmsFilmJob.objects.select_for_update().get(pk=job.pk)
        locked.outputs.all().delete()
        locked.delete()
    for asset in MediaAsset.objects.filter(pk__in=asset_ids, company=job.company):
        # A file that is still used elsewhere (a post, another job) stays in the media library.
        if asset_removal_blocker(asset) or asset.sms_film_files.exists() or asset.sms_film_outputs.exists():
            continue
        try:
            delete_file(asset)
        except MediaError:
            log.warning("sms-film radera: file %s could not be removed from storage", asset.pk)
            continue
        asset.delete()
