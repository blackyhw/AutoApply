from __future__ import annotations

import json
from typing import Any

from autoapply.errors import LlmError, LlmRateLimitError, LlmResponseError
from autoapply.llm.base import LlmRequest, LlmResponse
from autoapply.security.prompt_guard import SYSTEM_GUARDRAIL


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LlmError("GROQ_API_KEY is missing")
        self.api_key = api_key
        self.model = model

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        try:
            from groq import AsyncGroq
        except ImportError as exc:  # pragma: no cover
            raise LlmError("groq is not installed") from exc

        client = AsyncGroq(api_key=self.api_key)
        messages = request.messages
        if not any(m["role"] == "system" for m in messages):
            messages = [{"role": "system", "content": SYSTEM_GUARDRAIL}, *messages]
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_output_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            if status == 429 or "rate limit" in str(exc).lower():
                raise LlmRateLimitError(str(exc)) from exc
            raise LlmError(str(exc)) from exc

        text = completion.choices[0].message.content or ""
        data = _parse_json(text)
        return LlmResponse(data=data, provider=self.name, model=self.model, raw_text=text)


def _parse_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"Groq returned non-JSON: {text[:300]}") from exc
    if not isinstance(parsed, dict):
        raise LlmResponseError("Groq JSON root must be an object")
    return parsed
