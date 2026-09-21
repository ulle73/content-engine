"""Official OpenAI Images and Higgsfield REST contracts, checked 2026-09-08."""

import base64
import ipaddress
import os
import socket
import uuid
import random
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlparse

import httpx
from django.conf import settings
from openai import OpenAI

from .media_storage import MediaError, open_asset

HIGGS_ROOT = "https://api.higgsfield.ai"


class ProviderError(MediaError):
    code = "provider_error"
    transient = False


class InvalidProviderRequest(ProviderError):
    code = "invalid_request"


class ProviderAuthenticationError(ProviderError):
    code = "authentication_config"


class InsufficientCreditsError(ProviderError):
    code = "insufficient_credits"


class RateLimitedError(ProviderError):
    code = "rate_limited"
    transient = True


class ProviderUnavailableError(ProviderError):
    code = "provider_unavailable"
    transient = True


class UncertainGeneration(ProviderError):
    code = "uncertain_submission"
    transient = False


def provider_error_code(exc):
    return getattr(exc, "code", "provider_error")


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
    # Golfkuponger's Content Engine uses its dedicated Higgsfield API credential.
    # Keep the generic names as a backwards-compatible deployment fallback.
    key = (
        os.environ.get("HIGGSFIELD_API_KEY_GK", "").strip()
        or os.environ.get("HIGGSFIELD_API_KEY", "").strip()
    )
    secret = (
        os.environ.get("HIGGSFIELD_API_SECRET_GK", "").strip()
        or os.environ.get("HIGGSFIELD_API_SECRET", "").strip()
    )
    if not key:
        raise MediaError("Videogenerering behöver Golfkupongers Higgsfield API-nyckel i serverns inställningar.")
    if ":" in key or not secret:
        return key
    return f"{key}:{secret}"


def _error_for_response(method, response, *, billable=False):
    try:
        body = response.json()
        detail = body.get("detail") if isinstance(body, dict) else None
    except ValueError:
        detail = None
    status = response.status_code
    if detail == "not_enough_credits" or status == 403:
        return InsufficientCreditsError("Higgsfields API-konto saknar krediter. Fyll på API-saldot och försök igen.")
    if status == 401:
        return ProviderAuthenticationError("Higgsfield-autentiseringen är ogiltig. Kontrollera serverns API-nyckel.")
    if detail == "model_not_found" or status == 404:
        return InvalidProviderRequest("Videomodellen eller request-id är inte tillgängligt för API-kontot.")
    if status in {400, 422}:
        return InvalidProviderRequest("Higgsfield avvisade parametrarna. Ingen automatisk ny generation startades.")
    if status == 429:
        return RateLimitedError("Higgsfield har tillfälligt begränsat anropstakten.")
    if status in {423, 500, 502, 503, 504}:
        if billable:
            return UncertainGeneration(f"Higgsfield svarade med HTTP {status} efter ett möjligt betalt submit. Ingen automatisk retry görs.")
        return ProviderUnavailableError(f"Higgsfield är tillfälligt otillgängligt (HTTP {status}).")
    if billable and status >= 500:
        return UncertainGeneration(f"Higgsfield svarade med HTTP {status}. Ingen automatisk retry görs.")
    return ProviderError(f"Higgsfield svarade med HTTP {status}.")


def _retry_after_seconds(response, attempt):
    value = response.headers.get("Retry-After", "").strip()
    try:
        explicit = float(value)
        if explicit >= 0:
            return min(explicit, 5.0) + random.uniform(0, 0.25)
    except (TypeError, ValueError):
        pass
    return min(0.4 * (2 ** attempt), 2.0) + random.uniform(0, 0.25)


def higgs(method, path, *, billable=False, **kwargs):
    """Official REST adapter with method-aware retry safety.

    GET status reads may retry transient failures. POST is attempted exactly once
    because generation submissions currently have no idempotency key.
    """
    credential = _higgsfield_credential()
    method = method.upper()
    attempts = 3 if method == "GET" else 1
    last_error = None
    for attempt in range(attempts):
        try:
            response = httpx.request(method, HIGGS_ROOT + path, headers={"Authorization": f"Key {credential}"},
                                     timeout=40, **kwargs)
        except httpx.HTTPError as exc:
            if method == "GET" and attempt + 1 < attempts:
                time.sleep(min(0.4 * (2 ** attempt), 2.0) + random.uniform(0, 0.25))
                last_error = exc
                continue
            if billable:
                raise UncertainGeneration("Det betalda submit-anropet kunde inte bekräftas. Ingen automatisk ny generation görs.") from exc
            raise ProviderUnavailableError("Higgsfield kunde inte nås för detta säkra anrop.") from exc
        if response.is_error:
            error = _error_for_response(method, response, billable=billable)
            if method == "GET" and getattr(error, "transient", False) and attempt + 1 < attempts:
                time.sleep(_retry_after_seconds(response, attempt))
                last_error = error
                continue
            raise error
        try:
            return response.json()
        except ValueError as exc:
            if billable:
                raise UncertainGeneration("Higgsfield returnerade ett otydligt svar efter möjligt betalt submit. Ingen retry görs.") from exc
            raise ProviderUnavailableError("Higgsfields svar kunde inte läsas.") from exc
    raise ProviderUnavailableError("Higgsfields status kunde inte hämtas efter begränsade retries.") from last_error


def video_payload(job):
    # Kling's official schema accepts 5 or 10 seconds. I2V follows the source image.
    return {"prompt": job.prompt, "duration": int(job.parameters.get("duration", 10))}


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
    submit_path = "/" + model
    if getattr(settings, "HIGGSFIELD_WEBHOOK_ENABLED", False):
        webhook = settings.APP_URL.rstrip("/") + "/webhooks/higgsfield/"
        if webhook.startswith("https://"):
            submit_path += "?" + urlencode({"hf_webhook": webhook})
    result = higgs("POST", submit_path, json=body, billable=True)
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


def cancel_video(job):
    """Request cancellation only for a known provider request. Never submits generation."""
    request_id = str(uuid.UUID(job.provider_id))
    credential = _higgsfield_credential()
    try:
        response = httpx.request("POST", f"{HIGGS_ROOT}/requests/{request_id}/cancel",
                                 headers={"Authorization": f"Key {credential}"}, timeout=40)
    except httpx.HTTPError as exc:
        raise ProviderUnavailableError("Avbokningen kunde inte bekräftas. Kontrollera jobbstatus innan nytt försök.") from exc
    if response.status_code == 202:
        return True
    raise _error_for_response("CANCEL", response)
