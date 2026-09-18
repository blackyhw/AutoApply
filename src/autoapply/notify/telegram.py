from __future__ import annotations

from autoapply.logging import get_logger
from autoapply.notify.base import Notifier

log = get_logger("notify.telegram")


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send(self, title: str, body: str) -> None:
        if not self.configured():
            log.info("telegram_skipped", title=title)
            return
        try:
            import httpx
        except ImportError:  # pragma: no cover
            log.warning("httpx_missing")
            return
        text = f"*{title}*\n{body}"
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
            )
            response.raise_for_status()


_: Notifier = TelegramNotifier  # type: ignore[assignment]
