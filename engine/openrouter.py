"""Small OpenRouter adapter for cheap structured intelligence analysis.

The account-level @preset/gk-free route is tried first. If it errors or returns
invalid structured output, one explicit low-cost GLM 5.3 Flash fallback is
allowed. No retries are hidden inside httpx; the routing policy stays explicit.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
from typing import TypeVar

import httpx
from django.utils import timezone
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

API_URL = "https://openrouter.ai/api/v1/chat/completions"
logger = logging.getLogger(__name__)


class OpenRouterError(ValueError):
    """Safe user-facing provider error for non-side-effectful text analysis."""

    retryable = True

    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _content_text(message):
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        text = "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("text")
        ).strip()
        if text:
            return text
    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()
    reasoning_details = message.get("reasoning_details")
    if isinstance(reasoning_details, list):
        text = "".join(
            str(part.get("text", ""))
            for part in reasoning_details
            if isinstance(part, dict) and part.get("text")
        ).strip()
        if text:
            return text
    return ""


def _json_object(text):
    value = str(text or "").strip()
    value = re.sub(r"^\`\`\`(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*\`\`\`$", "", value)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Modellen returnerade inte JSON.") from None
        parsed = json.loads(value[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Modellen returnerade inte ett JSON-objekt.")
    return parsed


def _strict_json_schema(schema):
    """Make Pydantic object schemas explicit enough for strict JSON-schema providers."""
    value = copy.deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node.setdefault("additionalProperties", False)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return value


def _usage_meta(body, requested_model, operation):
    usage = body.get("usage") if isinstance(body, dict) else {}
    usage = usage if isinstance(usage, dict) else {}
    return {
        "provider": "openrouter",
        "service": "text",
        "operation": str(operation or "analysis")[:80],
        "model": str(body.get("model") or requested_model),
        "requested_model": requested_model,
        "response_id": str(body.get("id") or ""),
        "usage": usage,
        "cost_usd": usage.get("cost"),
        "recorded_at": timezone.now().isoformat(),
        "pricing_basis": "provider_reported",
    }


def _call(model, *, system, payload, schema, operation, max_tokens=4000, temperature=0, timeout_seconds=35, strict_schema=False, reasoning_effort=None, images=None, videos=None):
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise OpenRouterError(
            "OpenRouter är inte konfigurerat på Content Engine-servern. Lägg in OPENROUTER_API_KEY i Render."
        )

    schema_dict = _strict_json_schema(schema.model_json_schema())
    schema_name = re.sub(r"[^A-Za-z0-9_-]+", "_", schema.__name__)[:48] or "content_engine_output"
    schema_json = json.dumps(schema_dict, ensure_ascii=False, separators=(",", ":"))

    system_message = system
    request_body = {
        "model": model,
        "messages": [],
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "plugins": [{"id": "response-healing"}],
        "provider": {"sort": "throughput"},
        "usage": {"include": True},
    }
    if reasoning_effort:
        request_body["reasoning"] = {"effort": reasoning_effort}

    if strict_schema:
        system_message += "\nSvara kort och konkret. Svaret måste följa det påtvingade JSON-schemat exakt."
        request_body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema_dict,
            },
        }
        request_body["provider"]["require_parameters"] = True
    else:
        # Presets/free routers can contain endpoints that do not support native
        # json_schema. JSON object mode keeps the free route compatible while
        # the explicit schema in the prompt plus Pydantic validation still
        # prevents unvalidated data from reaching the product.
        system_message += (
            "\nReturnera ENDAST ett kompakt JSON-objekt som följer detta schema exakt. "
            "Ingen markdown eller annan text.\nSCHEMA:\n" + schema_json
        )
        request_body["response_format"] = {"type": "json_object"}

    request_body["messages"] = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    if images or videos:
        # Only trusted server code supplies bounded media (assistant uploads, cut-critic frames or finished cuts).
        request_body["messages"][1]["content"] = [
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False)},
            *[{"type": "video_url", "video_url": {"url": value}} for value in videos or []],
            *[{"type": "image_url", "image_url": {"url": value}} for value in images or []],
        ]
    try:
        response = httpx.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Content Engine",
            },
            json=request_body,
            timeout=httpx.Timeout(timeout_seconds, connect=5.0, read=timeout_seconds, write=10.0, pool=5.0),
        )
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise OpenRouterError("OpenRouter svarade inte i tid. Försök igen.", status_code=503) from exc

    if response.status_code < 200 or response.status_code >= 300:
        safe_detail = ""
        try:
            error_body = response.json()
            raw_detail = (
                (error_body.get("error") or {}).get("message")
                if isinstance(error_body.get("error"), dict)
                else error_body.get("message")
            )
            safe_detail = str(raw_detail or "").strip()[:300]
        except ValueError:
            safe_detail = ""
        if response.status_code == 429:
            message = "OpenRouter är tillfälligt rate-limitad."
        elif response.status_code == 402:
            message = "OpenRouter-kontot saknar tillgängliga credits för den här modellen."
        elif response.status_code in {401, 403}:
            message = "OpenRouter-autentiseringen fungerar inte. Kontrollera API-nyckeln i Render."
        elif response.status_code == 404:
            message = "OpenRouter-modellen eller preset-routen hittades inte för detta konto."
        elif response.status_code >= 500:
            message = "OpenRouter eller modellleverantören är tillfälligt otillgänglig."
        else:
            message = f"OpenRouter avvisade analysen (HTTP {response.status_code})."
        if safe_detail and response.status_code not in {404}:
            message += " " + safe_detail
        logger.warning("OpenRouter structured attempt failed model=%s status=%s detail=%s", model, response.status_code, safe_detail)
        raise OpenRouterError(message, status_code=response.status_code)

    try:
        body = response.json()
    except ValueError as exc:
        raise OpenRouterError("OpenRouter returnerade ett ogiltigt svar.", status_code=502) from exc
    choices = body.get("choices") if isinstance(body, dict) else None
    message = choices[0].get("message", {}) if isinstance(choices, list) and choices else {}
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    if choice.get("finish_reason") == "length":
        # Reasoning tokens count against max_completion_tokens. A cut-off answer can still look like JSON
        # (the reasoning fallback below, or a partly healed object), so it is never parsed.
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
        logger.warning(
            "OpenRouter answer cut off requested_model=%s response_model=%s max_tokens=%s completion_tokens=%s reasoning_tokens=%s",
            model, body.get("model"), max_tokens, usage.get("completion_tokens"), details.get("reasoning_tokens"),
        )
        raise OpenRouterError("Modellens svar klipptes av vid tokentaket.", status_code=502)
    try:
        parsed = schema.model_validate(_json_object(_content_text(message)))
    except (ValueError, ValidationError, json.JSONDecodeError) as exc:
        logger.warning(
            "OpenRouter structured validation failed requested_model=%s response_model=%s finish_reason=%s error=%s",
            model,
            body.get("model") if isinstance(body, dict) else "",
            choice.get("finish_reason"),
            str(exc)[:500],
        )
        raise OpenRouterError("Modellen returnerade inte ett giltigt strukturerat svar.", status_code=502) from exc
    return parsed, _usage_meta(body, model, operation)


def structured_assistant(*, system, payload, schema: type[T], images=None):
    """One bounded vision/text planning request, no automatic paid fallback or media tools."""
    model = os.environ.get("OPENROUTER_ASSISTANT_MODEL", "google/gemini-2.5-flash").strip() or "google/gemini-2.5-flash"
    return _call(model, system=system, payload=payload, schema=schema, operation="assistant_plan",
                 max_tokens=2400, temperature=0.1, timeout_seconds=40, strict_schema=True, images=images)


def structured_generation(*, system, payload, schema: type[T], operation="generation", max_tokens=2000, temperature=0.1):
    """Reliable low-cost generation path.

    Content generation intentionally skips the flaky free preset. GLM 5.3 Flash
    is cheap enough for these small outputs and OpenRouter can fail over across
    providers serving the same model. Reasoning stays enabled at low effort and
    the model returns native structured output.
    """
    model = (os.environ.get("OPENROUTER_GENERATION_MODEL", "").strip() or os.environ.get("OPENROUTER_ANALYSIS_FALLBACK_MODEL", "z-ai/glm-5.3-flash").strip() or "z-ai/glm-5.3-flash")
    try:
        return _call(
            model,
            system=system,
            payload=payload,
            schema=schema,
            operation=operation,
            max_tokens=max(max_tokens, 4000),
            temperature=temperature,
            timeout_seconds=40,
            strict_schema=True,
            reasoning_effort="low",
        )
    except OpenRouterError as exc:
        logger.warning("OpenRouter generation failed model=%s status=%s detail=%s", model, exc.status_code, exc)
        raise OpenRouterError(
            "AI-anropet kunde inte slutföras. Försök igen.",
            status_code=exc.status_code,
        ) from exc


def analysis_route():
    """Free preset first, then the low-cost fallback, then an optional last resort (e.g. Gemini Flash)."""
    free_model = os.environ.get("OPENROUTER_ANALYSIS_MODEL", "@preset/gk-free").strip() or "@preset/gk-free"
    paid_model = os.environ.get("OPENROUTER_ANALYSIS_FALLBACK_MODEL", "z-ai/glm-5.3-flash").strip() or "z-ai/glm-5.3-flash"
    last_resort = os.environ.get("OPENROUTER_ANALYSIS_LAST_RESORT_MODEL", "").strip()
    return list(dict.fromkeys(m for m in (free_model, paid_model, last_resort) if m))


def route_signature():
    return "openrouter:" + ">".join(analysis_route())


def video_model():
    """Model that watches whole videos with sound (Gemini via OpenRouter); defaults to the vision tier."""
    return os.environ.get("OPENROUTER_VIDEO_MODEL", "").strip() or vision_model()


def vision_model():
    """The image-capable tier of the analysis route (Gemini 3.1 Flash-Lite unless configured otherwise)."""
    return (os.environ.get("OPENROUTER_VISION_MODEL", "").strip()
            or os.environ.get("OPENROUTER_ANALYSIS_LAST_RESORT_MODEL", "").strip()
            or "google/gemini-3.1-flash-lite")


# Text answers here are a few hundred tokens, but reasoning shares the max_completion_tokens budget
# (openrouter.ai/docs/use-cases/reasoning-tokens). The free preset's models reason 1 100–1 900 tokens whatever
# effort is asked for, so the cap leaves room for that; it is a ceiling, not spend.
TEXT_ROUTE_MIN_TOKENS = 6000


def structured_analysis(*, system, payload, schema: type[T], operation="analysis", max_tokens=4000, temperature=0,
                        images=None, videos=None):
    """Free preset → GLM → last resort. With `images` (data URLs) only the vision tier is used: the free preset and
    GLM cannot see images, so trying them would only add latency. With `videos` (data:video/mp4 URLs, sound
    included) only the video tier is used (video_model())."""
    media = bool(images or videos)
    route = [video_model()] if videos else [vision_model()] if images else analysis_route()
    errors = []

    for model in route:
        try:
            is_fallback = model != route[0]
            timeout_seconds = 30 if not is_fallback else 35
            route_max_tokens = max_tokens if media else max(max_tokens, TEXT_ROUTE_MIN_TOKENS)
            # GLM 5.3 Flash always reasons and defaults to effort "max", which used the whole budget before any
            # answer. The paid tiers reason at low effort like structured_generation; the free preset ignores it.
            reasoning_effort = "low" if is_fallback and not media else None
            return _call(
                model,
                system=system,
                payload=payload,
                schema=schema,
                operation=operation,
                max_tokens=route_max_tokens,
                temperature=temperature,
                timeout_seconds=90 if videos else 40 if images else timeout_seconds,
                strict_schema=False,
                reasoning_effort=reasoning_effort,
                images=images,
                videos=videos,
            )
        except OpenRouterError as exc:
            errors.append((model, exc))
            if exc.status_code in {401, 403} or "inte konfigurerat" in str(exc):
                break

    if errors:
        details = " | ".join(f"{model}: {exc}" for model, exc in errors)
        logger.warning("OpenRouter structured route exhausted: %s", details)
        raise OpenRouterError(
            "AI-anropet kunde inte slutföras via OpenRouter. " + details,
            status_code=errors[-1][1].status_code,
        ) from errors[-1][1]
    raise OpenRouterError("AI-anropet kunde inte startas via OpenRouter.")
