from __future__ import annotations

import smtplib
from email.message import EmailMessage

from autoapply.logging import get_logger
from autoapply.notify.base import Notifier
from autoapply.settings import Settings

log = get_logger("notify.email")


class EmailNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def configured(self) -> bool:
        return bool(self.settings.agent_email_smtp_host and self.settings.alert_email)

    async def send(self, title: str, body: str) -> None:
        if not self.configured():
            log.info("email_skipped", title=title)
            return
        message = EmailMessage()
        message["From"] = self.settings.agent_email
        message["To"] = self.settings.alert_email
        message["Subject"] = title
        message.set_content(body)
        with smtplib.SMTP(self.settings.agent_email_smtp_host, self.settings.agent_email_smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if self.settings.agent_email_smtp_username:
                smtp.login(self.settings.agent_email_smtp_username, self.settings.agent_email_smtp_password)
            smtp.send_message(message)


_: Notifier = EmailNotifier  # type: ignore[assignment]
