import pytest

from autoapply.errors import LlmRateLimitError
from autoapply.llm.base import LlmRequest, LlmResponse
from autoapply.llm.router import LlmRouter


class _Primary:
    name = "gemini"

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        raise LlmRateLimitError("429")


class _Fallback:
    name = "groq"

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        return LlmResponse(data={"ok": True}, provider=self.name, model="llama")


@pytest.mark.asyncio
async def test_router_falls_back_on_rate_limit():
    router = LlmRouter(_Primary(), _Fallback())
    result = await router.complete_json(
        LlmRequest(messages=[], schema_name="x", schema={})
    )
    assert result.provider == "groq"
    assert result.data["ok"] is True
