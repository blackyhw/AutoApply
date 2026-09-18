from autoapply.collectors.base import VacancyCollector, fingerprint
from autoapply.collectors.dedupe import Deduper
from autoapply.collectors.registry import build_collectors

__all__ = ["Deduper", "VacancyCollector", "build_collectors", "fingerprint"]
