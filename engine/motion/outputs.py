"""Fenced, idempotent ingestion into Content Engine's existing media store."""

from __future__ import annotations
import hashlib
import io
import uuid
import av
from django.db import transaction
from django.utils import timezone
from engine.media import describe_file, store_asset, store_derived_image, select_asset
from engine.media_storage import MediaError
from engine.models import MediaAsset, MediaGeneration
from .jobs import leased_job
from .models import MotionRender, MotionKeyframe
from .schema import timeline

SIZES = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}


def expected_size(spec, mode):
    scale = 3 if mode == "preview" else 1
    return tuple(value // scale for value in SIZES[spec["aspect_ratio"]])


def keyframe_positions(spec):
    result = {}
    for scene, timing in zip(spec["scenes"], timeline(spec)):
        result[scene["id"]] = min(
            timing["end"] - 1,
            timing["start"] + max(scene["transition_frames"] + 1, int(scene["duration_frames"] * 0.7)),
        )
    return result


def manifest(job):
    """Only the immutable revision's media IDs, never arbitrary URLs or R2 credentials."""
    assets = []
    for ref in job.revision.asset_references.select_related("asset").all():
        asset = ref.asset
        if asset.company_id != job.revision.project.company_id or asset.sha256 != ref.sha256:
            raise ValueError("En k\u00e4llfil har \u00e4ndrats. Skapa en ny projektversion.")
        assets.append(
            {
                "id": str(asset.id),
                "kind": asset.kind,
                "mime_type": asset.mime_type,
                "sha256": ref.sha256,
                "byte_size": asset.byte_size,
                "width": asset.width,
                "height": asset.height,
                "duration_seconds": asset.duration_seconds,
            }
        )
    return {
        "render_id": str(job.id),
        "lease": str(job.lease_token),
        "mode": job.mode,
        "spec_hash": job.revision.spec_hash,
        "spec": job.revision.spec,
        "brand": job.revision.brand,
        "assets": assets,
    }


def validate_output(data, spec, mode):
    """Bounded header/first-frame checks. The worker separately decodes every frame."""
    if not data or len(data) > 80 * 1024 * 1024:
        raise ValueError("Videon m\u00e5ste vara mellan 1 byte och 80 MB.")
    width, height = expected_size(spec, mode)
    expected_frames = timeline(spec)[-1]["end"]
    expected_seconds = expected_frames / spec["fps"]
    try:
        with av.open(io.BytesIO(data)) as container:
            stream = next(iter(container.streams.video), None)
            audio = next(iter(container.streams.audio), None)
            if (
                not stream
                or stream.codec_context.name != "h264"
                or not audio
                or audio.codec_context.name != "aac"
                or len(container.streams.video) != 1
            ):
                raise ValueError("Utdata ska vara en MP4 med H.264-video och AAC-ljud.")
            if (stream.width, stream.height) != (width, height):
                raise ValueError("Videons uppl\u00f6sning matchar inte projektets format.")
            if not stream.average_rate or abs(float(stream.average_rate) - spec["fps"]) > 0.001:
                raise ValueError("Videons bildfrekvens matchar inte projektet.")
            if stream.duration is None or not stream.time_base:
                raise ValueError("Videon saknar verifierbar l\u00e4ngd.")
            seconds = float(stream.duration * stream.time_base)
            if abs(seconds - expected_seconds) > 0.5 / spec["fps"]:
                raise ValueError("Videons l\u00e4ngd matchar inte projektets tidslinje.")
            if stream.frames and stream.frames != expected_frames:
                raise ValueError("Videon inneh\u00e5ller fel antal bildrutor.")
            if stream.codec_context.format.name != "yuv420p":
                raise ValueError("Videon m\u00e5ste ha kompatibelt yuv420p-pixelformat.")
            if next(container.decode(video=0), None) is None:
                raise ValueError("Videon saknar l\u00e4sbar bild.")
            return {
                "width": width,
                "height": height,
                "fps": spec["fps"],
                "duration_frames": expected_frames,
                "duration_seconds": seconds,
                "video_codec": "h264",
                "audio_codec": "aac",
            }
    except av.error.FFmpegError as exc:
        raise ValueError("Videofilen kunde inte avkodas.") from exc


@transaction.atomic
def save_keyframe(job_id, token, scene_id, frame, data):
    job = leased_job(job_id, token, lock=True)
    expected = keyframe_positions(job.revision.spec)
    if job.mode != "preview" or scene_id not in expected or type(frame) is not int or frame != expected[scene_id]:
        raise ValueError("Bildrutan matchar inte projektets storyboard.")
    try:
        metadata = describe_file(data)
    except MediaError as exc:
        raise ValueError(str(exc)) from exc
    if metadata["kind"] != "image" or (metadata["width"], metadata["height"]) != expected_size(
        job.revision.spec, "preview"
    ):
        raise ValueError("Bildrutan har fel typ eller uppl\u00f6sning.")
    digest = hashlib.sha256(data).hexdigest()
    previous = job.storyboard.select_related("asset").filter(scene_id=scene_id).first()
    if previous:
        if previous.asset.sha256 != digest or previous.frame != frame:
            raise ValueError("Bildrutan har redan sparats med annat inneh\u00e5ll.")
        return previous.asset
    asset_id = uuid.uuid5(job.generation_id, "motion-keyframe-" + scene_id)
    asset = store_derived_image(
        job.revision.project.company,
        data,
        generation=job.generation,
        asset_id=asset_id,
        alt_text=scene_id,
        brief=job.revision.project.title,
    )
    MotionKeyframe.objects.create(render=job, asset=asset, scene_id=scene_id, frame=frame)
    return asset


@transaction.atomic
def save_output(job_id, token, data):
    # A lost completion response may be retried with the same lease and exact bytes.
    try:
        token = uuid.UUID(str(token))
        job = (
            MotionRender.objects.select_for_update(of=("self",))
            .select_related("generation", "revision__project__company", "output_asset")
            .get(pk=job_id)
        )
    except (ValueError, MotionRender.DoesNotExist):
        raise ValueError("Ogiltigt renderjobb.") from None
    if job.generation.status == "completed" and job.lease_token == token and job.output_asset_id:
        if job.output_asset.sha256 != hashlib.sha256(data).hexdigest():
            raise ValueError("Renderresultatet har redan sparats med annat inneh\u00e5ll.")
        return job.output_asset
    job = leased_job(job_id, token, lock=True)
    if job.mode == "preview" and job.storyboard.count() != len(job.revision.spec["scenes"]):
        raise ValueError("Alla storyboard-bilder m\u00e5ste sparas innan preview-videon.")
    quality = validate_output(data, job.revision.spec, job.mode)
    MediaGeneration.objects.filter(pk=job.generation_id).update(status="saving", updated_at=timezone.now())
    asset = store_asset(
        job.revision.project.company,
        data,
        job=job.generation,
        index=0,
        alt_text=job.revision.project.title + (" (preview)" if job.mode == "preview" else ""),
    )
    if asset.sha256 != hashlib.sha256(data).hexdigest():
        raise ValueError("Den sparade videons kontrollsumma matchar inte renderresultatet.")
    MediaAsset.objects.filter(pk=asset.pk).update(expires_at=None)
    asset.expires_at = None
    job.output_asset = asset
    job.progress = 1
    job.diagnostics = {"quality": quality, "spec_hash": job.revision.spec_hash}
    job.save(update_fields=["output_asset", "progress", "diagnostics", "updated_at"])
    MediaGeneration.objects.filter(pk=job.generation_id).update(
        status="completed",
        error="",
        usage={
            "renderer": "remotion",
            "mode": job.mode,
            "spec_hash": job.revision.spec_hash,
            "render_id": str(job.id),
            **quality,
        },
        updated_at=timezone.now(),
    )
    project = job.revision.project
    project.refresh_from_db()
    if job.mode == "final" and project.current_revision == job.revision.number:
        select_asset(project.run, asset)
    return asset
