from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from autoapply.collectors.base import VacancyCollector
from autoapply.domain.enums import Portal
from autoapply.domain.models import Vacancy


class FileFeedCollector:
    """Local JSON feed used for development and the first pipeline tests."""

    name = "file_feed"

    def __init__(self, path: Path):
        self.path = path

    async def collect(self, profile=None) -> list[Vacancy]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        vacancies: list[Vacancy] = []
        for item in payload:
            posted = item.get("posted_at")
            vacancies.append(
                Vacancy(
                    portal=Portal(item.get("portal", "file_feed")),
                    external_id=str(item["external_id"]),
                    title=item["title"],
                    company=item["company"],
                    location=item.get("location", ""),
                    url=item["url"],
                    description=item.get("description", ""),
                    posted_at=datetime.fromisoformat(posted) if posted else None,
                    raw_payload=item,
                )
            )
        return vacancies


# Protocol check
_: VacancyCollector = FileFeedCollector  # type: ignore[assignment]
