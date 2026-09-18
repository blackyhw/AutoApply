from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from autoapply.logging import get_logger
from autoapply.settings import Settings

log = get_logger("notify.mailer")


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.agent_email_smtp_host)


def send_email(
    settings: Settings,
    *,
    to: str,
    subject: str,
    body: str,
    attachments: list[Path] | None = None,
) -> None:
    if not smtp_configured(settings):
        raise RuntimeError("SMTP is not configured for the dedicated mailbox")
    message = EmailMessage()
    message["From"] = settings.agent_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    for path in attachments or []:
        data = path.read_bytes()
        message.add_attachment(
            data,
            maintype="application",
            subtype="pdf" if path.suffix.lower() == ".pdf" else "octet-stream",
            filename=path.name,
        )
    with smtplib.SMTP(settings.agent_email_smtp_host, settings.agent_email_smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.agent_email_smtp_username:
            smtp.login(settings.agent_email_smtp_username, settings.agent_email_smtp_password)
        smtp.send_message(message)
    log.info("email_sent", to=to, subject=subject)
