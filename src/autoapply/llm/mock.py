from __future__ import annotations

from collections.abc import Callable

from autoapply.llm.base import LlmRequest, LlmResponse
from autoapply.llm.schemas import CoverLetterFields, MatchLlmOutput, MeetingLlmOutput


class MockProvider:
    """Deterministic provider for tests and dry local runs without API keys."""

    name = "mock"

    def __init__(self, responder: Callable[[LlmRequest], dict] | None = None):
        self._responder = responder

    async def complete_json(self, request: LlmRequest) -> LlmResponse:
        if self._responder:
            data = self._responder(request)
        elif request.schema_name == "match":
            data = MatchLlmOutput(
                score=0.86,
                should_apply=True,
                reasons=["Python/FastAPI overlap with the profile."],
                missing_requirements=[],
                selected_block_ids=["header", "summary_backend", "exp_api_platform", "skills_core"],
                cover_letter_fields=CoverLetterFields(
                    role="Backend Developer",
                    company="Example",
                    matching_skills_sentence="Mi perfil cubre Python, FastAPI y PostgreSQL.",
                    candidate_name="Nombre Apellido",
                    dedicated_email="jobs-agent@example.com",
                ),
            ).model_dump()
        elif request.schema_name == "meeting":
            data = MeetingLlmOutput(
                is_meeting_related=False,
                disposition="none",
                confidence=0.2,
            ).model_dump()
        else:
            data = {}
        return LlmResponse(data=data, provider=self.name, model="mock", raw_text="")
