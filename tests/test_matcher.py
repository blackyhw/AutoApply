import pytest

from autoapply.domain.enums import Portal
from autoapply.domain.models import Profile, Vacancy
from autoapply.generator.blocks import BlockCatalog
from autoapply.llm.mock import MockProvider
from autoapply.llm.router import LlmRouter
from autoapply.matcher.scorer import Matcher


@pytest.mark.asyncio
async def test_hard_reject_exclude_keywords(catalog: BlockCatalog):
    matcher = Matcher(LlmRouter(MockProvider()), catalog, threshold=0.7)
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
