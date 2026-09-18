from __future__ import annotations

from autoapply.collectors.base import VacancyCollector
from autoapply.domain.models import Vacancy
from autoapply.errors import CollectorNotConfigured


class ComputrabajoCollector:
    """Stub for Computrabajo. Implement against their search pages or API later."""

    name = "computrabajo"

    async def collect(self) -> list[Vacancy]:
        raise CollectorNotConfigured(
            "Computrabajo collector is a stub. Implement search + detail fetch "
            "on the isolated VM before enabling it in config."
        )


_: VacancyCollector = ComputrabajoCollector  # type: ignore[assignment]
