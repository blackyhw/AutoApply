from __future__ import annotations

import json
from typing import Any

from autoapply.errors import LlmError, LlmRateLimitError, LlmResponseError
from autoapply.llm.base import LlmRequest, LlmResponse
from autoapply.security.prompt_guard import SYSTEM_GUARDRAIL


def _is_rate_limit(exc: BaseException) -> bool:
    text = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status in {429, "429", "RESOURCE_EXHAUSTED"}:
        return True
    return any(token in text for token in ("429", "rate limit", "resource_exhausted", "quota"))


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LlmError("GEMINI_API_KEY is missing")
        self.api_key = api_key
        self.model = model

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise LlmError("google-genai is not installed") from exc

        client = genai.Client(api_key=self.api_key)
        system = next((m["content"] for m in request.messages if m["role"] == "system"), SYSTEM_GUARDRAIL)
        user = "\n\n".join(m["content"] for m in request.messages if m["role"] != "system")
        try:
            result = await client.aio.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            if _is_rate_limit(exc):
                raise LlmRateLimitError(str(exc)) from exc
            raise LlmError(str(exc)) from exc

        text = getattr(result, "text", None) or ""
        data = _parse_json(text)
        return LlmResponse(data=data, provider=self.name, model=self.model, raw_text=text)


def _parse_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"Gemini returned non-JSON: {text[:300]}") from exc
    if not isinstance(parsed, dict):
        raise LlmResponseError("Gemini JSON root must be an object")
    return parsed
