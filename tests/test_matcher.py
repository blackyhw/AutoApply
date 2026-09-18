import pytest

from autoapply.domain.enums import Portal
from autoapply.domain.models import Profile, Vacancy
from autoapply.generator.blocks import BlockCatalog
from autoapply.matcher.scorer import Matcher


@pytest.mark.asyncio
async def test_hard_reject_exclude_keywords(catalog: BlockCatalog):
    matcher = Matcher(catalog, threshold=0.7)
    profile = Profile(
        full_name="Ada",
        dedicated_email="jobs-agent@example.com",
        exclude_keywords=["unpaid", "commission-only"],
    )
    vacancy = Vacancy(
        portal=Portal.FILE_FEED,
        external_id="x",
        title="Unpaid internship",
        company="Moon",
        url="https://example.com/x",
        description="commission-only role",
    )
    decision = await matcher.score(vacancy, profile)
    assert decision.should_apply is False
    assert decision.score <= 0.2


@pytest.mark.asyncio
async def test_keyword_match_without_llm(catalog: BlockCatalog):
    matcher = Matcher(catalog, threshold=0.5)
    profile = Profile(
        full_name="Ada",
        dedicated_email="jobs-agent@example.com",
        target_roles=["Backend Developer"],
        keywords=["python", "fastapi", "postgresql"],
    )
    vacancy = Vacancy(
        portal=Portal.FILE_FEED,
        external_id="y",
        title="Senior Python Backend Developer",
        company="Acme",
        url="https://example.com/y",
        description="Python, FastAPI y PostgreSQL para APIs.",
    )
    decision = await matcher.score(vacancy, profile)
    assert decision.should_apply is True
    assert decision.score >= 0.5
    assert decision.selected_block_ids
