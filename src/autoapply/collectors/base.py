from __future__ import annotations

from hashlib import sha256
from typing import Protocol

from autoapply.domain.models import Profile, Vacancy


class VacancyCollector(Protocol):
    name: str

    async def collect(self, profile: Profile | None = None) -> list[Vacancy]:
        """Return vacancies from one portal. Must not mutate agent state."""


def fingerprint(vacancy: Vacancy) -> str:
    if vacancy.external_id:
        basis = f"{vacancy.portal.value}|{vacancy.external_id.strip().lower()}"
    else:
        basis = "|".join(
            [
                vacancy.portal.value,
                _norm(vacancy.title),
                _norm(vacancy.company),
                _norm(vacancy.location),
            ]
        )
    return sha256(basis.encode("utf-8")).hexdigest()


def _norm(value: str) -> str:
    return " ".join(value.lower().split())
