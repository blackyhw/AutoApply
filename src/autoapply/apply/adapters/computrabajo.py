from __future__ import annotations

from autoapply.apply.adapters.base import PortalApplyAdapter
from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.errors import ApplyError


class ComputrabajoApplyAdapter:
    portal = "computrabajo"

    async def apply(self, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
        raise ApplyError("Computrabajo apply adapter is a stub.")


_: PortalApplyAdapter = ComputrabajoApplyAdapter  # type: ignore[assignment]
