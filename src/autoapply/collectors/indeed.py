from __future__ import annotations

from autoapply.collectors.base import VacancyCollector
from autoapply.domain.models import Vacancy
from autoapply.errors import CollectorNotConfigured


class IndeedCollector:
    """Stub: prefer publisher/API access over brittle HTML scraping."""

    name = "indeed"

    async def collect(self) -> list[Vacancy]:
        raise CollectorNotConfigured(
            "Indeed collector is a stub. Wire the publisher API or a consented "
            "browser session on the isolated VM."
        )


_: VacancyCollector = IndeedCollector  # type: ignore[assignment]
