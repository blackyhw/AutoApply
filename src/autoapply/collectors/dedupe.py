from __future__ import annotations

from autoapply.collectors.base import fingerprint
from autoapply.domain.models import Vacancy
from autoapply.persistence.repositories import Repository


class Deduper:
    def __init__(self, repo: Repository):
        self.repo = repo

    def unseen(self, vacancies: list[Vacancy]) -> list[tuple[Vacancy, str]]:
        fresh: list[tuple[Vacancy, str]] = []
        seen_this_batch: set[str] = set()
        for vacancy in vacancies:
            fp = fingerprint(vacancy)
            if fp in seen_this_batch:
                continue
            seen_this_batch.add(fp)
            if self.repo.vacancy_exists(fp) or self.repo.get_application(fp) is not None:
                continue
            fresh.append((vacancy, fp))
        return fresh
