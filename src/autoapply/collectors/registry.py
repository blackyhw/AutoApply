from __future__ import annotations

from pathlib import Path

from autoapply.collectors.base import VacancyCollector
from autoapply.collectors.computrabajo import ComputrabajoCollector
from autoapply.collectors.file_feed import FileFeedCollector
from autoapply.collectors.indeed import IndeedCollector
from autoapply.collectors.linkedin import LinkedInCollector
from autoapply.errors import ConfigurationError
from autoapply.settings import Settings


def build_collectors(settings: Settings) -> list[VacancyCollector]:
    collectors: list[VacancyCollector] = []
    for name in settings.enabled_collectors:
        if name == "file_feed":
            collectors.append(FileFeedCollector(Path(settings.file_feed_path)))
        elif name == "linkedin":
            collectors.append(LinkedInCollector())
        elif name == "indeed":
            collectors.append(IndeedCollector())
        elif name == "computrabajo":
            collectors.append(ComputrabajoCollector())
        else:
            raise ConfigurationError(f"Unknown collector: {name}")
    return collectors
