"""Official OpenAI Images and Higgsfield REST contracts, checked 2026-09-08."""

import base64
import ipaddress
import os
import socket
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx
from django.conf import settings
from openai import OpenAI

from .media_storage import MediaError, open_asset

HIGGS_ROOT = "https://api.higgsfield.ai"


class UncertainGeneration(MediaError):
    pass


def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise MediaError("Leverantören gav en ogiltig fillänk.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise MediaError("Leverantörens fillänk kan inte användas.")
    except OSError as exc:
        raise MediaError("Leverantörens filserver kunde inte nås.") from exc
    return url


def download_output(url, limit=80 * 1024 * 1024):
    try:
        with httpx.stream("GET", public_url(url), timeout=120, follow_redirects=False) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > limit:
                    raise MediaError("Den genererade filen är för stor för denna version.")
            return bytes(data)
    except httpx.HTTPError as exc:
        raise MediaError("Resultatfilen kunde inte hämtas. Kontrollera status igen; ingen ny generation startas.") from exc


def generate_images(job):
    params = {"model": job.parameters.get("model", settings.OPENAI_IMAGE_MODEL), "prompt": job.prompt, "n": job.parameters["count"],
              "size": job.parameters["size"], "quality": "medium", "output_format": "png"}
    with OpenAI(timeout=240, max_retries=0) as client:
        if job.source_asset:
            with open_asset(job.source_asset, unbranded=True) as source:
                result = client.images.edit(image=("reference." + job.source_asset.storage_key.rsplit(".", 1)[-1],
                                                   source, job.source_asset.mime_type), **params)
        else:
            result = client.images.generate(**params)
    return [base64.b64decode(item.b64_json, validate=True) for item in result.data], (
        result.usage.model_dump() if result.usage else {}
    )


def _higgsfield_credential():
    """Return the complete Higgsfield credential without exposing it.

    Current Higgsfield UI/SDK can provide one complete API credential. Older
    Content Engine deployments stored key id + secret separately, so keep that
    format as a backwards-compatible fallback.
    """
    key = os.environ.get("HIGGSFIELD_API_KEY", "").strip()
    secret = os.environ.get("HIGGSFIELD_API_SECRET", "").strip()
    if not key:
        raise MediaError("Videogenerering behöver Higgsfields API-nyckel i serverns inställningar.")
    if ":" in key or not secret:
        return key
    return f"{key}:{secret}"


def higgs(method, path, **kwargs):
    credential = _higgsfield_credential()
    try:
        response = httpx.request(method, HIGGS_ROOT + path, headers={"Authorization": f"Key {credential}"},
                                 timeout=40, **kwargs)
        if response.is_error:
            try:
                body = response.json()
                detail = body.get("detail") if isinstance(body, dict) else None
            except ValueError:
                detail = None
            if detail == "not_enough_credits":
                raise MediaError("Higgsfields API-konto saknar krediter. Fyll på API-saldot på cloud.higgsfield.ai och försök igen.")
            if detail == "model_not_found":
                raise MediaError("Videomodellen är inte tillgänglig hos Higgsfield. Driftansvarig behöver kontrollera modellstödet.")
            error = UncertainGeneration if method == "POST" and response.status_code >= 500 else MediaError
            raise error(f"Higgsfield svarade med HTTP {response.status_code}. Kontrollera API-kontot.")
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UncertainGeneration("Anropet kunde inte bekräftas. Ingen automatisk ny generation görs.") from exc


def video_payload(job):
    # Kling's official schema accepts 5 or 10 seconds. I2V follows the source image.
    return {"prompt": job.prompt, "duration": 10}


def upload_input(asset):
    result = higgs("POST", "/files/generate-upload-url", json={"content_type": asset.mime_type})
    with open_asset(asset, unbranded=True) as source:
        try:
            # Storage receives only its upload headers, never the Higgsfield credential.
            response = httpx.put(public_url(result["upload_url"]), content=source.read(),
                                 headers=result["upload_headers"], timeout=90)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MediaError("Startbilden kunde inte skickas till videoleverantören.") from exc
    return public_url(result["public_url"])


def start_video(job):
    mode = "image-to-video" if job.source_asset else "text-to-video"
    model = job.parameters.get("model", settings.HIGGSFIELD_VIDEO_MODEL) + "/" + mode
    body = video_payload(job)
    if job.source_asset:
        body["image_url"] = upload_input(job.source_asset)
    estimate = higgs("POST", "/estimate/" + model, json=body)
    try:
        price = Decimal(estimate["usd"])
        if not price.is_finite() or price < 0 or price > Decimal(os.environ.get("HIGGSFIELD_MAX_USD", "2")):
            raise MediaError("Videons pris överskrider serverns kostnadsgräns. Ingen generation startades.")
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise MediaError("Videotjänsten kunde inte bekräfta priset. Ingen generation startades.") from exc
    usage = {"estimate": {k: estimate[k] for k in ("credits", "usd") if k in estimate}, "model": model}
    job.usage = usage
    job.save(update_fields=["usage"])
    result = higgs("POST", "/" + model, json=body)
    try:
        result["request_id"] = str(uuid.UUID(result["request_id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise UncertainGeneration("Videotjänsten bekräftade inte ett giltigt jobb-id.") from exc
    return result, usage


def video_status(job):
    # Construct the trusted API path; never forward auth to provider-supplied URLs.
    import uuid
    request_id = str(uuid.UUID(job.provider_id))
    return higgs("GET", f"/requests/{request_id}/status")
