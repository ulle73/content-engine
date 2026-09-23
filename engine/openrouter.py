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


def _call(model, *, system, payload, schema, operation, max_tokens=4000, temperature=0, timeout_seconds=35, strict_schema=False):
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
        "max_tokens": max_tokens,
        "plugins": [{"id": "response-healing"}],
        "provider": {"sort": "throughput"},
        "usage": {"include": True},
    }

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
    try:
        response = httpx.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Golfkuponger Content Engine",
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
    try:
        parsed = schema.model_validate(_json_object(_content_text(message)))
    except (ValueError, ValidationError, json.JSONDecodeError) as exc:
        choice = choices[0] if isinstance(choices, list) and choices else {}
        logger.warning(
            "OpenRouter structured validation failed requested_model=%s response_model=%s finish_reason=%s error=%s",
            model,
            body.get("model") if isinstance(body, dict) else "",
            choice.get("finish_reason") if isinstance(choice, dict) else "",
            str(exc)[:500],
        )
        raise OpenRouterError("Modellen returnerade inte ett giltigt strukturerat svar.", status_code=502) from exc
    return parsed, _usage_meta(body, model, operation)


def route_signature():
    free_model = os.environ.get("OPENROUTER_ANALYSIS_MODEL", "@preset/gk-free").strip() or "@preset/gk-free"
    paid_model = os.environ.get("OPENROUTER_ANALYSIS_FALLBACK_MODEL", "z-ai/glm-5.3-flash").strip() or "z-ai/glm-5.3-flash"
    return f"openrouter:{free_model}>{paid_model}"


def structured_analysis(*, system, payload, schema: type[T], operation="analysis", max_tokens=4000, temperature=0):
    free_model = os.environ.get("OPENROUTER_ANALYSIS_MODEL", "@preset/gk-free").strip() or "@preset/gk-free"
    paid_model = os.environ.get("OPENROUTER_ANALYSIS_FALLBACK_MODEL", "z-ai/glm-5.3-flash").strip() or "z-ai/glm-5.3-flash"
    errors = []

    for model in dict.fromkeys((free_model, paid_model)):
        try:
            is_fallback = model == paid_model and paid_model != free_model
            timeout_seconds = 18 if not is_fallback else 40
            route_max_tokens = max(max_tokens, 5000) if is_fallback else max_tokens
            return _call(
                model,
                system=system,
                payload=payload,
                schema=schema,
                operation=operation,
                max_tokens=route_max_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                strict_schema=is_fallback,
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
