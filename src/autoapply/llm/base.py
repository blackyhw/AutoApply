from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel


class JsonSchemaModel(BaseModel):
    pass


@dataclass(frozen=True, slots=True)
class LlmRequest:
    messages: list[dict[str, str]]
    schema_name: str
    schema: dict[str, Any]
    temperature: float = 0.2
    max_output_tokens: int = 1024
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LlmResponse:
    data: dict[str, Any]
    provider: str
    model: str
    raw_text: str = ""


class LlmProvider(Protocol):
    name: str

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        """Return parsed JSON that matches `request.schema`."""
