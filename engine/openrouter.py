"""Small OpenRouter adapter for cheap structured intelligence analysis.

The account-level @preset/gk-free route is tried first. If it errors or returns
invalid structured output, one explicit low-cost GLM 5.3 Flash fallback is
allowed. No retries are hidden inside httpx; the routing policy stays explicit.
"""
from __future__ import annotations

import json
import os
import re
from typing import TypeVar

import httpx
from django.utils import timezone
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

API_URL = "https://openrouter.ai/api/v1/chat/completions"


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
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("text")
        ).strip()
    reasoning = message.get("reasoning")
    return reasoning.strip() if isinstance(reasoning, str) else ""


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


def _call(model, *, system, payload, schema, operation):
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise OpenRouterError(
            "OpenRouter är inte konfigurerat på Content Engine-servern. Lägg in OPENROUTER_API_KEY i Render."
        )

    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
    request_body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    system
                    + "\nReturnera ENDAST ett kompakt JSON-objekt som följer detta schema exakt. "
                    + "Ingen markdown, inga kodblock och ingen dold resonemangstext.\nSCHEMA:\n"
                    + schema_json
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0.1,
        "max_tokens": 1800,
        "usage": {"include": True},
    }
    try:
        response = httpx.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Golfkuponger Content Engine",
            },
            json=request_body,
            timeout=60,
        )
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise OpenRouterError("OpenRouter svarade inte i tid. Försök igen.", status_code=503) from exc

    if response.status_code < 200 or response.status_code >= 300:
        if response.status_code == 429:
            message = "OpenRouter är tillfälligt rate-limitad. Försök igen."
        elif response.status_code in {401, 403}:
            message = "OpenRouter-autentiseringen fungerar inte. Kontrollera API-nyckeln i Render."
        elif response.status_code >= 500:
            message = "OpenRouter eller modellleverantören är tillfälligt otillgänglig."
        else:
            message = f"OpenRouter avvisade analysen (HTTP {response.status_code})."
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
        raise OpenRouterError("Modellen returnerade inte ett giltigt strukturerat analyssvar.", status_code=502) from exc
    return parsed, _usage_meta(body, model, operation)


def structured_analysis(*, system, payload, schema: type[T], operation="analysis"):
    free_model = os.environ.get("OPENROUTER_ANALYSIS_MODEL", "@preset/gk-free").strip() or "@preset/gk-free"
    paid_model = os.environ.get("OPENROUTER_ANALYSIS_FALLBACK_MODEL", "z-ai/glm-5.3-flash").strip() or "z-ai/glm-5.3-flash"
    errors = []

    for model in dict.fromkeys((free_model, paid_model)):
        try:
            return _call(model, system=system, payload=payload, schema=schema, operation=operation)
        except OpenRouterError as exc:
            errors.append((model, exc))
            if exc.status_code in {401, 403} or "inte konfigurerat" in str(exc):
                break

    if errors:
        raise OpenRouterError(
            "AI-analysen kunde inte slutföras via OpenRouter. Gratisrouten och den billiga GLM-fallbacken misslyckades; försök igen om en stund.",
            status_code=errors[-1][1].status_code,
        ) from errors[-1][1]
    raise OpenRouterError("AI-analysen kunde inte startas via OpenRouter.")
