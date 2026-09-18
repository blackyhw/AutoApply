from __future__ import annotations

from pathlib import Path

from autoapply.collectors.base import VacancyCollector
from autoapply.collectors.computrabajo import ComputrabajoCollector
from autoapply.collectors.file_feed import FileFeedCollector
from autoapply.collectors.http import PoliteClient
from autoapply.collectors.indeed import IndeedCollector
from autoapply.collectors.linkedin import LinkedInCollector
from autoapply.errors import ConfigurationError
from autoapply.settings import Settings


def build_collectors(settings: Settings) -> list[VacancyCollector]:
    client = PoliteClient(delay_seconds=settings.collector_delay_seconds)
    collectors: list[VacancyCollector] = []
    for name in settings.enabled_collectors:
        if name == "file_feed":
            collectors.append(FileFeedCollector(Path(settings.file_feed_path)))
        elif name == "linkedin":
            collectors.append(
                LinkedInCollector(
                    client,
                    max_per_portal=settings.collector_max_per_portal,
                    fetch_details=settings.fetch_job_details,
                )
            )
        elif name == "indeed":
            collectors.append(
                IndeedCollector(
                    client,
                    country_host=settings.indeed_host,
                    max_per_portal=settings.collector_max_per_portal,
                )
            )
        elif name == "computrabajo":
            collectors.append(
                ComputrabajoCollector(
                    client,
                    base_url=settings.computrabajo_base_url,
                    max_per_portal=settings.collector_max_per_portal,
                    fetch_details=settings.fetch_job_details,
                )
            )
        else:
            raise ConfigurationError(f"Unknown collector: {name}")
    return collectors
