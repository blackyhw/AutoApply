from __future__ import annotations

from pathlib import Path

from autoapply.apply.browser import apply_in_browser
from autoapply.apply.email_apply import apply_by_email
from autoapply.domain.enums import Portal
from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.logging import get_logger
from autoapply.settings import Settings

log = get_logger("apply.engine")


class ApplyEngine:
    """Email first, Playwright session second. Dry-run never submits."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.dry_run = settings.dry_run

    async def apply(self, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
        log.info(
            "apply_start",
            portal=vacancy.portal.value,
            title=vacancy.title,
            company=vacancy.company,
            dry_run=self.dry_run,
            has_email=bool(vacancy.apply_email),
            pdf=package.cv_pdf_path,
        )
        if self.dry_run:
            return ApplyOutcome(
                ok=True,
                confirmation_id="dry-run",
                detail=self._dry_run_detail(vacancy, package),
            )
        if vacancy.apply_email:
            return await apply_by_email(self.settings, vacancy, package)
        if vacancy.portal is Portal.FILE_FEED:
            return ApplyOutcome(ok=True, confirmation_id="file-feed", detail="no live portal")
        state = Path(self.settings.playwright_state_dir) / f"{vacancy.portal.value}.json"
        screenshots = Path(self.settings.generated_dir) / "screenshots"
        return await apply_in_browser(
            vacancy=vacancy,
            package=package,
            state_path=state,
            screenshot_dir=screenshots,
            dry_run=False,
        )

    def _dry_run_detail(self, vacancy: Vacancy, package: ApplicationPackage) -> str:
        if vacancy.apply_email:
            channel = f"email:{vacancy.apply_email}"
        elif vacancy.portal is Portal.FILE_FEED:
            channel = "file_feed"
        else:
            channel = f"browser:{vacancy.portal.value}"
        return f"dry_run via {channel}; pdf={package.cv_pdf_path or '-'}"
