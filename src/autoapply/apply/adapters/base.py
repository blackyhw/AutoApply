from __future__ import annotations

from typing import Protocol

from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy


class PortalApplyAdapter(Protocol):
    portal: str

    async def apply(self, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
        ...
