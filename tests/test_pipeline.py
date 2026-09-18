import pytest

from autoapply.orchestrator import Agent
from autoapply.settings import Settings


@pytest.mark.asyncio
async def test_once_cycle_applies_match_and_rejects_excluded(settings: Settings):
    agent = Agent(settings)
    stats = await agent.run_once()
    assert stats["collected"] == 2
    assert stats["new"] == 2
    # sample-001 matches keyword overlap; sample-002 is keyword-excluded
    assert stats["applied"] == 1
    assert stats["rejected"] == 1
    assert stats["review"] == 0
    generated = list(settings.generated_dir.glob("*.pdf"))
    assert generated and generated[0].read_bytes().startswith(b"%PDF")

    second = await agent.run_once()
    assert second["new"] == 0
