from __future__ import annotations

from autoapply.apply.adapters.base import PortalApplyAdapter
from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.errors import ApplyError


class IndeedApplyAdapter:
    portal = "indeed"

    async def apply(self, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
        raise ApplyError("Indeed apply adapter is a stub.")


_: PortalApplyAdapter = IndeedApplyAdapter  # type: ignore[assignment]
