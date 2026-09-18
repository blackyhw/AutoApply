from __future__ import annotations

from pathlib import Path

from autoapply.domain.models import ApplicationPackage, ApplyOutcome, Vacancy
from autoapply.notify.mailer import send_email, smtp_configured
from autoapply.settings import Settings


async def apply_by_email(settings: Settings, vacancy: Vacancy, package: ApplicationPackage) -> ApplyOutcome:
    if not vacancy.apply_email:
        return ApplyOutcome(ok=False, detail="vacancy has no apply_email")
    if not smtp_configured(settings):
        return ApplyOutcome(ok=False, detail="SMTP is not configured")
    attachments = []
    if package.cv_pdf_path:
        attachments.append(Path(package.cv_pdf_path))
    send_email(
        settings,
        to=vacancy.apply_email,
        subject=package.cover_subject or f"Postulación — {vacancy.title}",
        body=package.cover_letter,
        attachments=attachments,
    )
    return ApplyOutcome(ok=True, confirmation_id=f"email:{vacancy.apply_email}", detail="sent via dedicated mailbox")
