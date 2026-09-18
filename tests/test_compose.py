import pytest

from autoapply.domain.enums import Portal
from autoapply.domain.models import MatchDecision, Profile, Vacancy
from autoapply.generator.blocks import BlockCatalog
from autoapply.generator.compose import compose_application
from autoapply.llm.mock import MockProvider
from autoapply.llm.router import LlmRouter
from autoapply.llm.schemas import CoverLetterFields, MatchLlmOutput


def _profile() -> Profile:
    return Profile(
        full_name="Ada",
        dedicated_email="jobs-agent@example.com",
        target_roles=["Backend Developer"],
        keywords=["python", "fastapi"],
    )


def _vacancy() -> Vacancy:
    return Vacancy(
        portal=Portal.FILE_FEED,
        external_id="y",
        title="Senior Python Backend Developer",
        company="Acme",
        url="https://example.com/y",
        description="Python y FastAPI.",
    )


def _heuristic() -> MatchDecision:
    return MatchDecision(
        score=0.81,
        should_apply=True,
        reasons=["phrase_hits=3/4"],
        selected_block_ids=["header", "skills_core"],
        cover_letter_fields={"role": "Backend", "company": "Acme"},
    )


@pytest.mark.asyncio
async def test_compose_keeps_heuristic_score_and_drops_unknown_blocks(catalog: BlockCatalog):
    def responder(request):
        assert request.schema_name == "compose"
        return MatchLlmOutput(
            score=0.99,
            should_apply=True,
            reasons=["Python overlap"],
            selected_block_ids=["header", "not_a_real_block", "exp_api_platform"],
            cover_letter_fields=CoverLetterFields(
                role="Backend Developer",
                company="Acme",
                matching_skills_sentence="Mi perfil cubre Python y FastAPI.",
                candidate_name="Ada",
                dedicated_email="jobs-agent@example.com",
            ),
        ).model_dump()

    decision = await compose_application(
        LlmRouter(MockProvider(responder)),
        catalog,
        _vacancy(),
        _profile(),
        _heuristic(),
    )
    assert decision.score == 0.81
    assert decision.should_apply is True
    assert "not_a_real_block" not in decision.selected_block_ids
    assert "header" in decision.selected_block_ids
    assert "exp_api_platform" in decision.selected_block_ids
    assert decision.cover_letter_fields["company"] == "Acme"


@pytest.mark.asyncio
async def test_compose_falls_back_to_heuristic_when_llm_fails(catalog: BlockCatalog):
    class Boom:
        name = "boom"

        async def complete_json(self, request):
            raise RuntimeError("quota")

    heuristic = _heuristic()
    decision = await compose_application(
        LlmRouter(Boom()),
        catalog,
        _vacancy(),
        _profile(),
        heuristic,
    )
    assert decision is heuristic
