from __future__ import annotations

from autoapply.apply.adapters.base import PortalApplyAdapter
from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.errors import ApplyError


class LinkedInApplyAdapter:
    portal = "linkedin"

    async def apply(self, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
        raise ApplyError("LinkedIn apply adapter is a stub. Implement Playwright Easy Apply on the isolated VM.")


_: PortalApplyAdapter = LinkedInApplyAdapter  # type: ignore[assignment]
