from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings


class LLMError(RuntimeError):
    pass


@dataclass(slots=True)
class LLMResult:
    data: dict[str, Any]
    provider: str
    model: str
    fallback_used: bool = False


def _extract_json_object(text: str) -> dict[str, Any]:
    value = (text or "").strip()
    if value.startswith("```"):
        value = value.strip("`").strip()
        if value.lower().startswith("json"):
            value = value[4:].strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise LLMError("LLM did not return a JSON object")
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON returned by LLM: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM JSON root must be an object")
    return parsed


def chat_json(system_prompt: str, user_prompt: str) -> LLMResult:
    settings = get_settings()
    provider = settings.llm_provider.strip().lower()
    if provider == "mock":
        raise LLMError("mock provider does not make an LLM call")
    if provider != "ollama":
        raise LLMError(f"Unsupported LLM_PROVIDER={settings.llm_provider!r}; use ollama or mock")

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": settings.llm_temperature},
    }
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMError(f"Ollama request failed: {exc}") from exc

    content = ((body.get("message") or {}).get("content") or "").strip()
    return LLMResult(
        data=_extract_json_object(content),
        provider="ollama",
        model=str(body.get("model") or settings.ollama_model),
    )
