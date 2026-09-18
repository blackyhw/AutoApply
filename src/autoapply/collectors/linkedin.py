from __future__ import annotations

from autoapply.collectors.base import VacancyCollector
from autoapply.domain.models import Vacancy
from autoapply.errors import CollectorNotConfigured


class LinkedInCollector:
    """Stub: official API or authenticated session on the isolated VM.

    Do not scrape logged-out HTML at scale. Configure credentials in the VM
    secrets volume when this adapter is implemented.
    """

    name = "linkedin"

    def __init__(self, session_dir: str | None = None):
        self.session_dir = session_dir

    async def collect(self) -> list[Vacancy]:
        raise CollectorNotConfigured(
            "LinkedIn collector is a stub. Provide an official API token or a "
            "Playwright storage_state captured on the isolated VM, then implement collect()."
        )


_: VacancyCollector = LinkedInCollector  # type: ignore[assignment]
