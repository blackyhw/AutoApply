from __future__ import annotations

from autoapply.apply.adapters.computrabajo import ComputrabajoApplyAdapter
from autoapply.apply.adapters.indeed import IndeedApplyAdapter
from autoapply.apply.adapters.linkedin import LinkedInApplyAdapter
from autoapply.domain.enums import Portal
from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.errors import ApplyError
from autoapply.logging import get_logger

log = get_logger("apply.engine")


class ApplyEngine:
    """Dispatches to a portal adapter. Dry-run never touches the network."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.adapters = {
            Portal.LINKEDIN: LinkedInApplyAdapter(),
            Portal.INDEED: IndeedApplyAdapter(),
            Portal.COMPUTRABAJO: ComputrabajoApplyAdapter(),
        }

    async def apply(self, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
        if self.dry_run:
            log.info(
                "dry_run_apply",
                portal=vacancy.portal.value,
                title=vacancy.title,
                company=vacancy.company,
                blocks=package.selected_block_ids,
            )
            return ApplyOutcome(ok=True, confirmation_id="dry-run", detail="dry_run")

        adapter = self.adapters.get(vacancy.portal)
        if adapter is None:
            if vacancy.portal is Portal.FILE_FEED:
                return ApplyOutcome(ok=True, confirmation_id="file-feed", detail="no live portal")
            raise ApplyError(f"No apply adapter for portal {vacancy.portal}")
        return await adapter.apply(vacancy, package)
