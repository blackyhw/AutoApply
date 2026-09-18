from __future__ import annotations

from autoapply.logging import get_logger
from autoapply.notify.base import Notifier
from autoapply.notify.mailer import send_email, smtp_configured
from autoapply.settings import Settings

log = get_logger("notify.email")


class EmailNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def configured(self) -> bool:
        return smtp_configured(self.settings) and bool(self.settings.alert_email)

    async def send(self, title: str, body: str) -> None:
        if not self.configured():
            log.info("email_skipped", title=title)
            return
        send_email(self.settings, to=self.settings.alert_email, subject=title, body=body)
